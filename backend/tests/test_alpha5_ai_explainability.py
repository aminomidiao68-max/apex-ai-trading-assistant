from __future__ import annotations

import asyncio

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
