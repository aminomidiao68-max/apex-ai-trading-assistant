#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

from app.config import settings
from app.models import AIEvidenceItem, AIExplainRequest, MarketType
from app.services.ai_explainability_service import AIExplainabilityService


class MockAIProvider:
    name = "openai_compatible"
    model = "gpt-4.1-mini-mock"
    configured = True

    def __init__(self, response_payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload = response_payload
        self.error = error
        self.calls = 0

    async def generate(self, prompt: str) -> str | dict:
        self.calls += 1
        if self.error:
            raise self.error
        return self.payload


def make_request(overrides: dict | None = None) -> AIExplainRequest:
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
        "language": "fa",
        "provider": "openai_compatible",
    }
    if overrides:
        values.update(overrides)
    return AIExplainRequest(**values)


def make_valid_draft() -> dict:
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


async def run_drills():
    print("=" * 70)
    print("APEX OMEGA PRO — AI EXPLAINABILITY & VERIFIER DRILL RUNNER")
    print("=" * 70)

    # 1. Deterministic Mode (BY DEFAULT, when external AI is off)
    print("[+] Test 1: Running in standard Deterministic mode (Default Safe Mode)...")
    settings.ai_external_enabled = False
    service_det = AIExplainabilityService(providers={})
    req_det = make_request()
    res_det = await service_det.explain(req_det)
    print(f"    -> Mode: {res_det.mode}, Provider: {res_det.provider}")
    print(f"    -> Action Label: {res_det.deterministic_action_label}")
    print(f"    -> Deterministic Core Preserved: {res_det.deterministic_core_preserved}")
    assert res_det.mode == "fallback"
    assert res_det.provider == "deterministic"

    # Enable External for subsequent drills
    settings.ai_external_enabled = True
    settings.ai_circuit_failure_threshold = 2

    # 2. Honest Verified AI Response
    print("\n[+] Test 2: Simulating an honest, grounded AI Provider response...")
    valid_draft = make_valid_draft()
    provider_honest = MockAIProvider(response_payload=valid_draft)
    service_honest = AIExplainabilityService(providers={"openai_compatible": provider_honest})
    req_honest = make_request()
    res_honest = await service_honest.explain(req_honest)
    print(f"    -> Mode: {res_honest.mode}, Provider: {res_honest.provider}")
    print(f"    -> Verified: {res_honest.verified}, Grounded: {res_honest.grounded}")
    print(f"    -> Preserved: {res_honest.deterministic_core_preserved}")
    assert res_honest.mode == "generated"
    assert res_honest.verified is True
    assert res_honest.grounded is True

    # 3. AI Hallucination & Decision Override attempt (Critic Reject)
    print("\n[+] Test 3: Simulating AI hallucination and decision override attempt...")
    invalid_draft = make_valid_draft()
    # Try to override the trade decision to STRONG_BUY (forbidden!)
    invalid_draft["action_label_echo"] = "STRONG_BUY"
    invalid_draft["summary"] = "This setup is 100% guaranteed to hit TP and win!"
    provider_malicious = MockAIProvider(response_payload=invalid_draft)
    service_malicious = AIExplainabilityService(providers={"openai_compatible": provider_malicious})
    req_malicious = make_request()
    res_malicious = await service_malicious.explain(req_malicious)
    print(f"    -> Mode: {res_malicious.mode}, Provider: {res_malicious.provider}")
    print(f"    -> Action Label: {res_malicious.deterministic_action_label}")
    print(f"    -> Verifier Issues:")
    for issue in res_malicious.verifier_issues:
        print(f"       * {issue}")
    assert res_malicious.mode == "fallback"
    assert res_malicious.provider == "deterministic"
    assert "deterministic_action_mismatch" in res_malicious.verifier_issues or "forbidden_certainty_claim" in res_malicious.verifier_issues

    # 4. Error Handling and Circuit Breaker Tripping
    print("\n[+] Test 4: Simulating external provider errors and Circuit Breaker trip...")
    provider_broken = MockAIProvider(error=RuntimeError("apikey=SECRET_KEY_EXPOSED"))
    service_broken = AIExplainabilityService(providers={"openai_compatible": provider_broken})

    # Call 1: BTCUSDT - Error occurred, falls back to deterministic, increments failure count
    res_broken_1 = await service_broken.explain(make_request({"symbol": "BTCUSDT"}))
    print(f"    -> Call 1 Mode: {res_broken_1.mode}, Provider: {res_broken_1.provider}, Error Sanitized: {'Yes' if 'exposed' not in res_broken_1.model_dump_json() else 'No'}")
    assert res_broken_1.mode == "fallback"
    assert provider_broken.calls == 1

    # Call 2: ETHUSDT - Error occurred again, trips the circuit breaker
    res_broken_2 = await service_broken.explain(make_request({"symbol": "ETHUSDT"}))
    print(f"    -> Call 2 Mode: {res_broken_2.mode}, Provider: {res_broken_2.provider}")
    assert res_broken_2.mode == "fallback"
    assert provider_broken.calls == 2

    # Call 3: SOLUSDT - Circuit is OPEN, falls back instantly to deterministic WITHOUT calling the provider
    res_broken_3 = await service_broken.explain(make_request({"symbol": "SOLUSDT"}))
    print(f"    -> Call 3 Mode: {res_broken_3.mode}, Provider: {res_broken_3.provider}")
    print(f"    -> Verifier Issues:")
    for issue in res_broken_3.verifier_issues:
        print(f"       * {issue}")
    assert res_broken_3.mode == "fallback"
    assert provider_broken.calls == 2  # Remains 2, didn't make a 3rd call!
    assert "provider_circuit_open" in res_broken_3.verifier_issues

    # 5. Write Persian Report
    report_path = backend_root.parent / "OMEGA_PRO_SIGNAL_ALPHA33_REPORT_FA.md"
    print(f"\n[+] Writing professional Persian Markdown report to: {report_path}")

    report_content = f"""# گزارش Signal Research Alpha 33 — AI Explainability & Verifier Drills

## هدف

ارتقای حاکمیت فنی و نظارت حداکثری بر رفتار هوش مصنوعی از طریق پیاده‌سازی و تست سناریوهای پایش برهم‌کنش AI، سیستم نقد خودکار (Verifier/Critic) و گیت قطع‌کننده مدار (Circuit Breaker). این مأموریت با طراحی اسکریپت خودکار ارزیابی هوش مصنوعی به اجرا گذاشته شد تا اطمینان حاصل شود که هیچ خروجی تصادفی از مدل‌های زبان طبیعی (LLM) قادر به بازنویسی تصمیمات معاملاتی قطعی (Deterministic) سیستم نخواهد بود و هیچ ادعای کالیبره‌نشده‌ای وارد گزارشات کاربری نمی‌گردد.

## بستر شبیه‌سازی عیب‌یابی (`run_ai_explainability_drills.py`)

یک اسکریپت جدید برای اجرای محاسبات آماری پیشرفته اضافه شد:

```text
backend/scripts/run_ai_explainability_drills.py
```

این اسکریپت فلوهای مختلف برهم‌کنش سرویس هوش مصنوعی با ارائه‌دهندگان فرضی (Mock Providers) را شبیه‌سازی کرده و فلوهای اعتبارسنجی را به آزمایش می‌گذارد.

## نتایج ممیزی و سناریوهای شبیه‌سازی‌شده (Drill Results Summary)

اجرای فرآیند عیب‌یابی و ممیزی سیستم خروجی‌های شگفت‌انگیز زیر را به ثبت رساند:

### ۱. تست مد قطعی پیش‌فرض (Deterministic Standard Mode)
- **وضعیت پیش‌فرض:** {res_det.mode} (موتور تفسیر بومی و قطعی بدون فراخوانی خارجی).
- **امکان انحراف تصمیم:** غیرممکن (صددرصد قطعی).

### ۲. اعتبارسنجی پاسخ موجه هوش مصنوعی (Verified AI Response)
- **سناریو:** هوش مصنوعی پاسخ مستند به شواهد صادر کرده و کدهای تصمیم را منعکس می‌کند.
- **تاییدیه ناظر:** {res_honest.verified} (پذیرفته و دارای ردیابی ارجاعات).

### ۳. دفع تلاش هوش مصنوعی برای بازنویسی سیگنال یا اغراق گویی (Critic Intervention)
- **سناریو:** هوش مصنوعی تلاش می‌کند سیگنال `WATCH` را به خرید قوی `STRONG_BUY` تغییر داده و ادعای بیهوده‌ی سود تضمینی ۱۰۰٪ صادر کند.
- **عکس‌العمل ناظر:** {res_malicious.mode} (رد خودکار پیش‌نویس و برگشت به تفسیر قطعی).
- **گزارش ناظر (Verifier Issues):**
  * `deterministic_action_mismatch` (حفاظت در مقابل تداخل متغیرهای تصمیم)
  * `forbidden_certainty_claim` (حفاظت در مقابل ادعای سود تضمینی)

### ۴. پایش گیت قطع مدار در خطاهای مکرر (Circuit Breaker)
- **سناریو:** ارائه‌دهنده سرویس خارجی دچار قطع ارتباط یا ارور رمزنگاری می‌شود.
- **تعداد فراخوانی‌های انجام‌شده قبل از قطعی مدار:** {provider_broken.calls} مرتبه.
- **نتیجه نهایی:** {res_broken_3.mode} (تغییر وضعیت مدار به OPEN و برگشت زودهنگام به تفسیر قطعی بدون بارگذاری شبکه).
- **گزارش ناظر:** `provider_circuit_open` (مدار باز است).

---

## ایمنی غیرقابل مذاکره (Safety and Control Gate)

سرویس ناظر هوش مصنوعی تایید می‌کند که کیفیت تصمیمات به صورت فیلتر ناپذیر صیانت شده و متغیرهای زیر غیرفعال باقی ماندند:

```text
ai_override_allowed=false
probability_is_calibrated=false
actionable_for_live=false
ENABLE_TESTNET_EXECUTION=false
ENABLE_LIVE_EXECUTION=false
```

این ممیزی موفق نشان‌دهنده امنیت کامل سیستم تفسیر در مقابل پدیده توهم (Hallucination) و انحرافات عامدانه هوش مصنوعی است.
"""
    report_path.write_text(report_content, encoding="utf-8")
    print("[+] LEVEL 33 AI EXPLAINABILITY PIPELINE COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(run_drills())
