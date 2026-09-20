"""v3.31 honest-edge layer: no invented win rates, negative edge cannot trade."""

from app.services import honest_edge
from app.services.strategy_grounded_helper import StrategyGroundedHelper as Helper


def test_measured_win_rate_replaces_marketing_claim():
    s = Helper.map_setup_to_handbook("LIQUIDITY SWEEP MSS")
    assert s["win_rate_is_measured"] is True
    assert s["measured_edge"]["detector"] == "liquidity_sweep"
    # the old marketing range is kept only for audit, never as the shown value
    assert s["win_rate"] != s["win_rate_claimed_unvalidated"]
    assert s["tradeable"] is False


def test_unmeasured_setup_reports_gap_not_a_number():
    v = honest_edge.edge_verdict(None)
    assert v["measured"] is False
    assert v["tradeable"] is False
    assert v["win_rate_fa"] == honest_edge.UNMEASURED_FA


def test_positive_edge_detector_is_tradeable():
    v = honest_edge.edge_verdict("triangle_break")
    assert v["measured"] is True and v["tradeable"] is True
    assert v["stats"]["profit_factor"] > 1.0


def test_no_handbook_entry_exposes_a_claimed_number_as_win_rate():
    for setup in ("FVG", "ORDER BLOCK", "WYCKOFF SPRING", "BREAKOUT", "PINBAR"):
        s = Helper.map_setup_to_handbook(setup)
        assert "الی" not in s["win_rate"], setup


def test_ict_prompt_section_has_no_marketing_win_rates():
    text = Helper.get_ict_pack_prompt_section()
    assert "۶۵٪ الی ۷۵٪" not in text
    assert "اندازه‌گیری‌شده" in text
