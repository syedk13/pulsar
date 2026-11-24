"""Scenario acceptance on the in-process synthetic dataset (same seed as the loader).

These assert what model `baseline-iforest-0.1.0` actually does on seed 2026, documented in
docs/api-contract.md. Where it falls short of docs/synthetic-data.md section 6, the test says
so instead of hiding it.
"""

import pytest

from app.ml import AnalysisResult, Checkin, analyze_checkin
from app.synthetic import generate
from app.synthetic.config import DEFAULT_SEED


@pytest.fixture(scope="module")
def results() -> dict[str, list[tuple[int, AnalysisResult]]]:
    ds = generate(DEFAULT_SEED)
    codes = {p["id"]: p["profile_code"] for p in ds.tables["crew_profiles"]}
    by_profile: dict[str, list[tuple[int, Checkin]]] = {}
    for r in ds.tables["health_checkins"]:
        checkin = Checkin(
            r["id"],
            r["recorded_at"],
            r["sleep_duration_hours"],
            r["resting_heart_rate"],
            r["mood_rating"],
        )
        by_profile.setdefault(codes[r["profile_id"]], []).append(
            (r["data_quality"]["mission_day"], checkin)
        )
    out = {}
    for code, rows in by_profile.items():
        rows.sort(key=lambda x: x[1].recorded_at)
        checkins = [c for _, c in rows]
        out[code] = [(day, analyze_checkin(c, checkins[:i])) for i, (day, c) in enumerate(rows)]
    return out


def flagged(rows, lo=1, hi=60):
    return [(d, r) for d, r in rows if r.label == "worth_reviewing" and lo <= d <= hi]


def named(result: AnalysisResult) -> set[str]:
    return {c.feature for c in result.contributing_changes}


def test_crew_a_stable_is_mostly_within_baseline(results):
    scored = [r for _, r in results["CREW-A"] if r.label != "insufficient_data"]
    within = sum(r.label == "within_baseline" for r in scored)
    assert within / len(scored) >= 0.8  # actual: 42 of 49
    # The S4 schedule shift (days 20-21, sleep -1 h for everyone) shows as a short dip.
    assert {d for d, _ in flagged(results["CREW-A"], 20, 21)} == {20, 21}


def test_crew_b_sleep_decline_is_flagged_with_sleep_named(results):
    in_window = flagged(results["CREW-B"], 42, 50)
    assert any("sleep_duration_hours" in named(r) for _, r in in_window)
    # Known gap vs the spec ("from about day 42", sleep and mood): the first flag is day 46,
    # because the rolling 14-check-in baseline follows a gradual decline, and mood's 1-point
    # steps stay within 2 spreads. Asserted so a change in behaviour is noticed.
    assert min(d for d, _ in in_window) == 46
    assert not any("mood_rating" in named(r) for _, r in in_window)


def test_crew_c_rhr_trend_flags_resting_heart_rate_only(results):
    in_window = flagged(results["CREW-C"], 42, 49)
    assert len(in_window) >= 2  # actual: days 45, 46, 47
    assert all(named(r) == {"resting_heart_rate"} for _, r in in_window)


def test_crew_d_new_profile_is_collecting_baseline(results):
    rows = results["CREW-D"]
    assert len(rows) == 5
    assert all(r.label == "insufficient_data" and r.score is None for _, r in rows)


def test_every_flag_names_what_changed(results):
    for rows in results.values():
        for _, r in rows:
            if r.label == "worth_reviewing":
                assert r.contributing_changes
                assert "worth reviewing" in r.explanation
