"""v3.30 QUALITY-ONLY: no artificial count caps + probability display tiers.

User policy (2026-09-19): the old "1-2 setups per week" was an EXAMPLE, not a
cap. Selection is by QUALITY ONLY — a day may yield several elite setups, a
week may yield none. Setups with estimated win probability >=70-80% must be
DISPLAYED (watch tiers), while truly actionable signals keep the elite gates.
Estimated probability is an UNCALIBRATED model estimate, never a promise.
"""
import inspect

from app.services import smc_engine
from app.services.intraday_fusion_service import IntradayFusionService
from tests.test_zero_error_v326 import _report, _strict


# ---------- no artificial caps ----------

def test_omega_caps_removed():
    assert smc_engine.OMEGA_MAX_DAILY_TRADES == -1
    assert smc_engine.OMEGA_MAX_WEEKLY_TRADES == -1


def test_fusion_has_no_quota_parameter():
    params = inspect.signature(IntradayFusionService.fuse).parameters
    assert "quota" not in params


def test_signal_quota_service_is_gone():
    import importlib
    import pytest
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("app.services.signal_quota_service")


# ---------- display tiers (display only, never actionable) ----------

def test_actionable_baseline_is_actionable_tier():
    d = _strict(_report(probability=90, grade="A+"))["decision"]
    assert d["status"] == "actionable"
    assert d["display_tier"] == "ACTIONABLE"
    assert d["estimated_win_probability"] == 90


def test_prob_84_grade_a_is_high_confidence_watch():
    d = _strict(_report(probability=84, grade="A"))["decision"]
    assert d["status"] == "watch"          # NOT actionable
    assert d["display_tier"] == "HIGH_CONFIDENCE_WATCH"
    assert d["estimated_win_probability"] == 84


def test_prob_72_grade_a_is_prob_watch_70():
    d = _strict(_report(probability=72, grade="A"))["decision"]
    assert d["display_tier"] == "PROB_WATCH_70"
    assert d["status"] != "actionable"


def test_prob_72_grade_b_plus_still_displayed():
    d = _strict(_report(probability=72, grade="B+"))["decision"]
    assert d["display_tier"] == "PROB_WATCH_70"


def test_prob_69_is_not_displayed():
    d = _strict(_report(probability=69, grade="A"))["decision"]
    assert d["display_tier"] == "NONE"


def test_news_blocked_kills_all_watch_tiers():
    d = _strict(_report(probability=84, grade="A+", news_blocked=True))["decision"]
    assert d["display_tier"] == "NONE"
