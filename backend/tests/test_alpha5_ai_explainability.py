from __future__ import annotations

import asyncio
import json

import pytest

from app.config import settings
from app.models import AIEvidenceItem, AIExplainRequest, MarketType
from app.services.ai_explainability_service import (
    AIExplainabilityService,
    build_evidence_request_from_report,
)


class _FakeProvider:
    name = "openai_compatible"
    model = "fake-grounded-model"
    configured = True

    def __init__(self, payload=None, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error
        self.calls = 0

    async def generate(self, prompt: str):
        self.calls += 1
        assert "EVIDENCE_PACKET_JSON" in prompt
        if self.error:
            raise self.error
        return self.payload


def _request(**overrides) -> AIExplainRequest:
    values = {
        "symbol": "BTCUSDT",
        "market": MarketType.crypto,
        "timeframe": "15m",
        "deterministic_status": "watch",
        "deterministic_action_label": "WATCH",
        "side": "long",
        "risk_tier": "blocked",
        "evidence": [
            AIEvidenceItem(
                evidence_id="E_STRUCTURE",
                category="structure",
                statement="Deterministic market structure evidence is present.",
                source="strict_core",
                polarity="positive",
            )
        ],
        "negative_evidence": [
            AIEvidenceItem(
                evidence_id="N_SPREAD",
                category="hard_gate",
                statement="The measured execution-spread gate failed policy.",
                source="strict_core",
                polarity="negative",
            )
        ],
        "failed_gates": ["execution_spread"],
        "invalidation": "No active trade thesis; reassess only after failed hard gates change.",
        "probability_estimate": 71,
        "probability_is_calibrated": False,
        "probability_label": "model_estimate_not_calibrated",
        "language": "en",
        "provider": "openai_compatible",
    }
    values.update(overrides)
    return AIExplainRequest(**values)


def _valid_draft() -> dict:
    return {
        "summary": "The deterministic decision remains watch-only because execution evidence is incomplete.",
        "evidence_ids": ["E_STRUCTURE"],
        "negative_evidence_ids": ["N_SPREAD"],
        "risk_notes": [
            {"text": "The execution-spread gate failed policy.", "evidence_ids": ["N_SPREAD"]}
        ],
        "what_would_confirm": [
            {"text": "Resolve the measured execution-spread gate.", "evidence_ids": ["N_SPREAD"]}
        ],
        "invalidation": "No active trade thesis; reassess only after failed hard gates change.",
        "action_label_echo": "WATCH",
        "probability_label_echo": "model_estimate_not_calibrated",
    }


def _enable_external(monkeypatch):
    monkeypatch.setattr(settings, "ai_external_enabled", True)
    monkeypatch.setattr(settings, "ai_provider", "openai_compatible")
    monkeypatch.setattr(settings, "ai_cache_ttl_seconds", 90)
    monkeypatch.setattr(settings, "ai_circuit_failure_threshold", 2)
    monkeypatch.setattr(settings, "ai_circuit_cooldown_seconds", 120)


def test_verified_external_explanation_is_cited_cached_and_cannot_override(monkeypatch):
    _enable_external(monkeypatch)
    provider = _FakeProvider(_valid_draft())
    service = AIExplainabilityService(providers={"openai_compatible": provider})
    request = _request()

    first = asyncio.run(service.explain(request))
    second = asyncio.run(service.explain(request))

    assert first.mode == "generated"
    assert first.provider == "openai_compatible"
    assert first.external_ai_used is True
    assert first.verified is True and first.grounded is True
    assert first.deterministic_action_label == "WATCH"
    assert first.deterministic_core_preserved is True
    assert first.probability_is_calibrated is False
    assert first.probability_label == "model_estimate_not_calibrated"
    assert second.cached is True
    assert provider.calls == 1


@pytest.mark.parametrize(
    ("mutation", "expected_issue"),
    [
        (lambda d: d.update({"action_label": "LONG", "action_label_echo": "LONG"}), "forbidden_control_fields"),
        (lambda d: d.update({"evidence_ids": ["E_INVENTED"]}), "unsupported_evidence_citation"),
        (lambda d: d.update({"summary": "This setup has a 92% guaranteed win rate."}), "forbidden_certainty_claim"),
        (lambda d: d.update({"invalidation": "Invented price level"}), "invalidation_mismatch"),
    ],
)
def test_critic_rejects_override_hallucination_probability_and_invalidation(
    monkeypatch, mutation, expected_issue
):
    _enable_external(monkeypatch)
    draft = _valid_draft()
    mutation(draft)
    provider = _FakeProvider(draft)
    service = AIExplainabilityService(providers={"openai_compatible": provider})

    result = asyncio.run(service.explain(_request()))

    assert result.mode == "fallback"
    assert result.provider == "deterministic"
    assert result.external_ai_used is False
    assert result.deterministic_action_label == "WATCH"
    assert expected_issue in result.verifier_issues
    assert "92%" not in result.summary


def test_missing_critical_data_refuses_before_provider_call(monkeypatch):
    _enable_external(monkeypatch)
    provider = _FakeProvider(_valid_draft())
    service = AIExplainabilityService(providers={"openai_compatible": provider})
    request = _request(invalidation=None, missing_data=["orderflow_source"])

    result = asyncio.run(service.explain(request))

    assert result.mode == "refusal"
    assert result.refusal_reason == "missing_critical_data"
    assert result.grounded is False
    assert result.deterministic_core_preserved is True
    assert provider.calls == 0


def test_provider_errors_are_sanitized_and_circuit_breaker_fails_closed(monkeypatch):
    _enable_external(monkeypatch)
    provider = _FakeProvider(error=RuntimeError("apikey=TOP_SECRET_VALUE"))
    service = AIExplainabilityService(providers={"openai_compatible": provider})

    first = asyncio.run(service.explain(_request(symbol="BTCUSDT")))
    second = asyncio.run(service.explain(_request(symbol="ETHUSDT")))
    third = asyncio.run(service.explain(_request(symbol="SOLUSDT")))

    assert first.mode == second.mode == third.mode == "fallback"
    assert provider.calls == 2
    assert "provider_unavailable" in first.verifier_issues
    assert "provider_circuit_open" in third.verifier_issues
    serialized = first.model_dump_json() + second.model_dump_json() + third.model_dump_json()
    assert "TOP_SECRET_VALUE" not in serialized
    assert "apikey=" not in serialized


def test_report_builder_preserves_honest_forex_proxy_and_negative_evidence():
    report = {
        "symbol": "EURUSD",
        "timeframe": "15m",
        "direction": "long",
        "probability": 73,
        "invalidation": 1.08,
        "decision": {
            "status": "watch",
            "action_label": "WATCH",
            "side": "long",
            "risk_tier": "blocked",
            "probability_is_calibrated": False,
            "probability_label": "model_estimate_not_calibrated",
            "failed_gates": ["htf_alignment"],
            "gates": [
                {"name": "data_quality", "passed": True, "actual": 95, "required": ">=78"},
                {"name": "htf_alignment", "passed": False, "actual": False, "required": "aligned"},
            ],
            "orderflow": {
                "source": "forex_ohlcv_proxy",
                "is_real": False,
                "confidence": 0.42,
                "pressure": "buy",
                "aligned": True,
            },
        },
        "confluence_factors": [{"name": "BOS", "points": 8}],
        "levels": {"sl": 1.08},
    }
    request = build_evidence_request_from_report(report, "forex", "15m")
    orderflow = next(item for item in request.evidence if item.evidence_id == "O_SOURCE")

    assert orderflow.is_real is False
    assert "proxy" in orderflow.statement.lower()
    assert "not centralized real" in orderflow.statement.lower()
    assert request.negative_evidence
    assert request.probability_is_calibrated is False
    assert request.probability_label == "model_estimate_not_calibrated"


def test_calibrated_probability_requires_traceable_calibration_id():
    with pytest.raises(ValueError, match="calibration_id"):
        _request(probability_is_calibrated=True, calibration_id=None)


def test_user_runtime_provider_is_opt_in_and_cache_is_user_scoped(monkeypatch):
    monkeypatch.setattr(settings, "ai_external_enabled", False)
    provider = _FakeProvider(_valid_draft())
    provider.name = "groq"
    service = AIExplainabilityService(providers={})
    request = _request(provider="groq")

    first = asyncio.run(
        service.explain(request, runtime_provider=provider, cache_namespace="user-1")
    )
    second_user = asyncio.run(
        service.explain(request, runtime_provider=provider, cache_namespace="user-2")
    )
    cached_first_user = asyncio.run(
        service.explain(request, runtime_provider=provider, cache_namespace="user-1")
    )

    assert first.mode == "generated"
    assert first.provider == "groq"
    assert second_user.cached is False
    assert cached_first_user.cached is True
    assert provider.calls == 2


# ------------------------------------------------- v3.18 multi-provider AI chain


def test_new_providers_registered_with_distinct_base_urls(monkeypatch):
    """Cerebras/Groq/OpenRouter are first-class providers with their own endpoints."""
    from app.services.provider_secret_service import (
        OPENAI_COMPATIBLE_BASE_URLS,
        PROVIDERS,
        _DEFAULT_MODELS,
    )
    for provider in ("cerebras", "groq", "openrouter", "openai"):
        assert provider in PROVIDERS
        assert provider in _DEFAULT_MODELS
    bases = list(OPENAI_COMPATIBLE_BASE_URLS.values())
    assert len(bases) == len(set(bases)), "base URLs must not collide"
    assert "cerebras.ai" in OPENAI_COMPATIBLE_BASE_URLS["cerebras"]
    assert "openrouter.ai" in OPENAI_COMPATIBLE_BASE_URLS["openrouter"]

    monkeypatch.setenv("AI_CEREBRAS_API_KEY", "cerebras-test-key")
    monkeypatch.setenv("AI_OPENROUTER_API_KEY", "openrouter-test-key")
    from app.services.ai_explainability_service import _default_providers

    providers = _default_providers()
    assert providers["cerebras"].configured is True
    assert providers["openrouter"].configured is True
    assert providers["cerebras"].base_url != providers["openrouter"].base_url
    assert "cerebras.ai" in providers["cerebras"].base_url


def test_status_exposes_fallback_chain_without_leaking_keys(monkeypatch):
    _enable_external(monkeypatch)
    monkeypatch.setenv("AI_CEREBRAS_API_KEY", "cerebras-secret-key")
    monkeypatch.setenv("AI_GROQ_API_KEY", "groq-secret-key")
    monkeypatch.setenv("AI_OPENROUTER_API_KEY", "openrouter-secret-key")
    from app.services.ai_explainability_service import AIExplainabilityService, _default_providers

    service = AIExplainabilityService(providers=_default_providers())
    status = service.status()
    chain = status["fallback_chain"]
    assert chain, "at least one configured provider must be listed"
    assert chain[0] == "cerebras", "cerebras leads the latency-ordered chain"
    assert "openrouter" in chain and "groq" in chain
    serialized = json.dumps(status).lower()
    assert "cerebras-secret-key" not in serialized
    assert "groq-secret-key" not in serialized
    assert "openrouter-secret-key" not in serialized
    assert "api_key" not in serialized


def test_chain_falls_over_to_next_provider_on_transport_error(monkeypatch):
    """A dead key must degrade to the next configured model, not to silence."""
    _enable_external(monkeypatch)
    dead = _FakeProvider(error=RuntimeError("401 invalid key"))
    dead.name = "cerebras"
    alive = _FakeProvider(_valid_draft())
    alive.name = "groq"
    service = AIExplainabilityService(providers={"cerebras": dead, "groq": alive})

    result = asyncio.run(service.explain(_request(provider="auto")))

    assert dead.calls == 1 and alive.calls == 1
    assert result.mode == "generated"
    assert result.provider == "groq"
    assert result.external_ai_used is True
    assert result.deterministic_action_label == "WATCH"
    assert result.deterministic_core_preserved is True


def test_verification_failure_does_not_fall_over_to_another_model(monkeypatch):
    """A hallucinating model fails closed — never laundered through a second model."""
    _enable_external(monkeypatch)
    bad = _FakeProvider(json.dumps({**_valid_draft(), "action_label": "LONG"}))
    bad.name = "cerebras"
    honest = _FakeProvider(_valid_draft())
    honest.name = "groq"
    service = AIExplainabilityService(providers={"cerebras": bad, "groq": honest})

    result = asyncio.run(service.explain(_request(provider="auto")))

    assert bad.calls == 1
    assert honest.calls == 0, "a verification failure must not retry with another model"
    assert result.mode == "fallback"
    assert result.provider == "deterministic"
    assert result.external_ai_used is False
    assert "forbidden_control_fields" in result.verifier_issues


def test_explicit_provider_request_pins_that_provider_only(monkeypatch):
    _enable_external(monkeypatch)
    pinned = _FakeProvider(_valid_draft())
    pinned.name = "openrouter"
    other = _FakeProvider(_valid_draft())
    other.name = "cerebras"
    service = AIExplainabilityService(providers={"openrouter": pinned, "cerebras": other})

    result = asyncio.run(service.explain(_request(provider="openrouter")))

    assert pinned.calls == 1 and other.calls == 0
    assert result.provider == "openrouter" and result.mode == "generated"


def test_all_providers_down_falls_back_to_deterministic(monkeypatch):
    _enable_external(monkeypatch)
    dead_a = _FakeProvider(error=RuntimeError("timeout"))
    dead_a.name = "cerebras"
    dead_b = _FakeProvider(error=RuntimeError("503"))
    dead_b.name = "openrouter"
    service = AIExplainabilityService(providers={"cerebras": dead_a, "openrouter": dead_b})

    result = asyncio.run(service.explain(_request(provider="auto")))

    assert dead_a.calls == dead_b.calls == 1
    assert result.mode == "fallback"
    assert result.provider == "deterministic"
    assert result.external_ai_used is False
    assert "provider_unavailable" in result.verifier_issues
    assert result.deterministic_action_label == "WATCH"


def test_ai_explain_layer_cannot_reach_execution(monkeypatch):
    """Hard invariant: enabling external AI must not touch any execution switch."""
    _enable_external(monkeypatch)
    monkeypatch.setenv("AI_CEREBRAS_API_KEY", "cerebras-secret-key")
    monkeypatch.setenv("AI_OPENROUTER_API_KEY", "openrouter-secret-key")
    from app.services.ai_explainability_service import AIExplainabilityService, _default_providers
    from pathlib import Path

    service = AIExplainabilityService(providers=_default_providers())
    result = asyncio.run(service.explain(_request(provider="auto")))

    assert result.deterministic_core_preserved is True
    # the explainer can only ever return evidence text + citations
    assert result.grounded is True or result.mode == "fallback"
    assert service.status()["deterministic_core_can_be_overridden"] is False

    # and the release blueprint keeps execution off while AI is on
    render = (Path(__file__).resolve().parents[2] / "render.yaml").read_text()
    assert "ENABLE_LIVE_EXECUTION\n        value: false" in render
    assert "ENABLE_TESTNET_EXECUTION\n        value: false" in render
    assert "AI_EXTERNAL_ENABLED\n        value: true" in render


def test_auto_and_deterministic_preferences_do_not_pin_the_chain(monkeypatch):
    """AI_PROVIDER=auto/deterministic must not make the catch-all slot lead."""
    _enable_external(monkeypatch)
    from app.services.ai_explainability_service import _configured_chain, _default_providers

    providers = _default_providers()
    providers["cerebras"].api_key = "cerebras-key"
    providers["openai_compatible"].api_key = "openai-key"
    providers["gemini"].api_key = "gemini-key"

    latency_first = _configured_chain(providers, "auto")
    assert latency_first[0] == "cerebras"
    assert latency_first == _configured_chain(providers, None)
    assert latency_first == _configured_chain(providers, "deterministic")

    # an explicit provider choice is still respected as a preference
    pinned = _configured_chain(providers, "openai_compatible")
    assert pinned[0] == "openai_compatible"
    assert set(pinned) == set(latency_first)
