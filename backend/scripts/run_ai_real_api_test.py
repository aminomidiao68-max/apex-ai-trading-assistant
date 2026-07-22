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


def make_request() -> AIExplainRequest:
    return AIExplainRequest(
        symbol="BTCUSDT",
        market=MarketType.crypto,
        timeframe="15m",
        deterministic_status="watch",
        deterministic_action_label="WATCH",
        side="long",
        risk_tier="blocked",
        evidence=[
            AIEvidenceItem(
                evidence_id="E_STRUCTURE",
                category="structure",
                statement="Deterministic market structure shows high volume bullish breakout.",
                source="strict_core",
                polarity="positive",
            )
        ],
        negative_evidence=[
            AIEvidenceItem(
                evidence_id="N_SPREAD",
                category="hard_gate",
                statement="The measured execution-spread is slightly above policy limits.",
                source="strict_core",
                polarity="negative",
            )
        ],
        failed_gates=["execution_spread"],
        invalidation="No active trade thesis; reassess only after failed hard gates change.",
        probability_estimate=71,
        probability_is_calibrated=False,
        probability_label="model_estimate_not_calibrated",
        language="fa",
        provider="openai_compatible",
    )


async def main():
    print("=" * 70)
    print("APEX OMEGA PRO — REAL OPENAI & GROQ INTEGRATION VERIFIER")
    print("=" * 70)

    # Load environment variables from active .env file
    api_key = os.getenv("AI_OPENAI_API_KEY", "").strip()
    base_url = os.getenv("AI_OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    model = os.getenv("AI_OPENAI_MODEL", "gpt-4.1-mini").strip()

    print(f"[+] Active API Configuration:")
    print(f"    -> Base URL: {base_url}")
    print(f"    -> Model:    {model}")
    print(f"    -> API Key:  {api_key[:6]}...{api_key[-4:] if len(api_key)>10 else ''}" if api_key else "    -> [WARNING] No API key detected in environment!")

    if not api_key:
        print("\n[!] Error: No AI_OPENAI_API_KEY found in your environment!")
        print("    Please set your OpenAI or Groq API key in your terminal or .env file:")
        print("    export AI_OPENAI_API_KEY=\"your_key_here\"")
        print("    export AI_OPENAI_BASE_URL=\"https://api.groq.com/openai/v1\"  # for Groq")
        print("    export AI_OPENAI_MODEL=\"llama-3.3-70b-versatile\"            # for Groq")
        return 1

    # Temporarily force external AI on for this test run
    original_enabled = settings.ai_external_enabled
    settings.ai_external_enabled = True
    settings.ai_provider = "openai_compatible"
    settings.ai_openai_api_key = api_key
    settings.ai_openai_base_url = base_url
    settings.ai_openai_model = model

    print("\n[+] Initializing AI Explainability Service with real provider credentials...")
    service = AIExplainabilityService()

    print("[+] Sending real API request to generate grounded market explanation...")
    req = make_request()
    
    start_time = asyncio.get_event_loop().time()
    try:
        response = await service.explain(req)
        elapsed = asyncio.get_event_loop().time() - start_time
        
        print(f"\n[+] API CALL COMPLETED SUCCESSFULLY in {elapsed:.2f} seconds!")
        print(f"    -> Mode:      {response.mode}")
        print(f"    -> Provider:  {response.provider}")
        print(f"    -> Verified:  {response.verified}")
        print(f"    -> Grounded:  {response.grounded}")
        print(f"    -> Verifier Issues: {response.verifier_issues}")
        print("\n[+] Generated Grounded Explanation (Summary):")
        print("-" * 60)
        print(response.summary)
        print("-" * 60)
        
    except Exception as exc:
        print(f"\n[-] API Call failed: {exc}")
        print("    Check your internet connection, API keys, or rate limits.")
    
    # Restore settings
    settings.ai_external_enabled = original_enabled
    return 0


if __name__ == "__main__":
    asyncio.run(main())
