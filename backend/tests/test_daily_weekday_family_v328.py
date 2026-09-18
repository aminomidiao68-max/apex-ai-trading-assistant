"""v3.28: daily bias context, weekday liquidity, evidence anti-inflation."""
from datetime import datetime, timezone

from app.services.strict_decision_engine import apply_strict_decision, evidence_inflation_points
from tests.test_zero_error_v326 import _candles, _report

NOW = datetime(2026, 9, 16, 13, 0, tzinfo=timezone.utc)      # Wednesday
SUNDAY = datetime(2026, 9, 20, 13, 0, tzinfo=timezone.utc)    # weekend


def _strict(report, now=NOW):
    return apply_strict_decision(report, _candles(), "crypto", "4h", now_utc=now)


def test_weekend_is_rejected():
    assert "weekday_liquidity" in _strict(_report(), now=SUNDAY)["decision"]["failed_gates"]
    assert "weekday_liquidity" not in _strict(_report(), now=NOW)["decision"]["failed_gates"]


def test_family_cap_deflates_double_counted_evidence():
    factors = [
        {"name": "liquidity sweep A", "points": 10},
        {"name": "liquidity sweep B", "points": 10},
        {"name": "liquidity grab C", "points": 10},   # same family: 30 raw -> 14 capped
        {"name": "HTF alignment", "points": 10},
        {"name": "BOS structure", "points": 10},
        {"name": "OTE entry", "points": 10},
    ]
    inflation = evidence_inflation_points(factors)
    assert inflation == 16.0  # 30 - 14
    dec = _strict(_report(confluence=90, confluence_factors=factors))
    assert dec["decision"]["confluence_effective"] == 74.0
    assert "confluence" in dec["decision"]["failed_gates"]


def test_diverse_evidence_is_not_deflated():
    factors = [
        {"name": "HTF alignment", "points": 10}, {"name": "BOS structure", "points": 10},
        {"name": "OTE entry", "points": 10}, {"name": "liquidity sweep", "points": 10},
    ]
    assert evidence_inflation_points(factors) == 0.0
    dec = _strict(_report(confluence=90, confluence_factors=factors))
    assert dec["decision"]["confluence_effective"] == 90.0
    assert "confluence" not in dec["decision"]["failed_gates"]


def test_fusion_requires_daily_bias_alignment():
    from app.services.intraday_fusion_service import IntradayFusionService
    from tests.test_weekly_grade_v325 import _fusion_frames

    frames = _fusion_frames()
    daily = next(f for f in frames if f["timeframe"] == "1d")
    daily["report"]["direction"] = "short"
    daily["report"]["bias"] = "bearish"
    daily["report"]["decision"]["side"] = "short"
    daily["report"]["decision"]["orderflow"]["pressure"] = "sell"
    result = IntradayFusionService().fuse("BTCUSDT", "crypto", frames, now_utc=NOW)
    assert "daily_bias_aligned" in result["failed_gates"]
    assert result["status"] != "ACTIONABLE_CANDIDATE"


def test_fusion_all_frames_includes_daily():
    from app.services.intraday_fusion_service import IntradayFusionService
    from tests.test_weekly_grade_v325 import _fusion_frames

    frames = [f for f in _fusion_frames() if f["timeframe"] != "1d"]
    result = IntradayFusionService().fuse("BTCUSDT", "crypto", frames, now_utc=NOW)
    assert "all_frames_available" in result["failed_gates"]
