"""Unit tests for app/ml (pure functions)."""

import re
from datetime import timedelta

import pytest

from app.ml import MODEL_VERSION, Checkin, analyze_checkin
from app.ml.model import reference_model
from tests.conftest import make_checkins, steady, steady_rows

FORBIDDEN = re.compile(r"\b(risk|condition|disease|predict\w*)\b", re.IGNORECASE)


def nxt(history: list[Checkin], sleep, rhr, mood, cid="target") -> Checkin:
    return Checkin(cid, history[-1].recorded_at + timedelta(days=1), sleep, rhr, mood)


def test_no_checkins_is_collecting_baseline():
    r = analyze_checkin(None, [])
    assert r.label == "insufficient_data"
    assert r.score is None and r.checkin_id is None and r.contributing_changes == []
    assert "Collecting baseline" in r.explanation
    assert r.model_version == MODEL_VERSION


def test_fewer_than_7_earlier_checkins_is_insufficient():
    history = steady(6)
    r = analyze_checkin(nxt(history, 6.5, 60, 4), history)
    assert r.label == "insufficient_data"
    assert r.score is None
    assert "6 earlier check-ins so far" in r.explanation
    assert r.details["window"]["baseline_checkins"] == 6


def test_exactly_7_earlier_checkins_is_scored():
    history = steady(7)
    r = analyze_checkin(nxt(history, 6.5, 60, 4), history)
    assert r.label == "within_baseline"
    assert r.score is not None and 0 < r.score < 1
    assert r.details["window"]["baseline_checkins"] == 7
    assert "your 7 earlier check-ins" in r.explanation


def test_baseline_uses_only_the_last_14_checkins():
    # 6 old check-ins with very different values, then a steady 14.
    history = make_checkins([(3.0, 100.0, 1.0)] * 6 + steady_rows(14))
    r = analyze_checkin(nxt(history, 6.5, 60, 4), history)
    window = r.details["window"]
    assert window["baseline_checkins"] == 14
    assert window["from"] == history[6].recorded_at.isoformat()
    assert r.details["indicators"]["sleep_duration_hours"]["baseline"] == 6.5
    assert r.details["indicators"]["resting_heart_rate"]["baseline"] == 60.0
    assert "median of your last 14 check-ins" in r.explanation
    assert r.label == "within_baseline"


def test_null_value_in_scored_checkin_is_not_compared():
    history = steady(14)
    r = analyze_checkin(nxt(history, 6.5, 60, None), history)
    mood = r.details["indicators"]["mood_rating"]
    assert mood["status"] == "not_recorded"
    assert "Mood was not recorded in this check-in" in r.explanation
    assert r.label == "within_baseline"


def test_nulls_in_history_are_skipped_not_zero():
    rows = [(6.5 if i % 3 else None, 60.0, 4.0) for i in range(14)]  # 9 sleep values, 5 nulls
    history = make_checkins(rows)
    r = analyze_checkin(nxt(history, 6.5, 60, 4), history)
    sleep = r.details["indicators"]["sleep_duration_hours"]
    assert sleep["values_in_window"] == 9
    assert sleep["baseline"] == 6.5  # a zero-filled median would be lower


def test_indicator_with_fewer_than_7_values_is_left_out():
    rows = [(6.5, 60.0, 4.0 if i < 6 else None) for i in range(14)]  # only 6 mood values
    history = make_checkins(rows)
    r = analyze_checkin(nxt(history, 6.5, 60, 2), history)
    assert r.details["indicators"]["mood_rating"]["status"] == "short_history"
    assert "Mood has only 6 recorded values" in r.explanation
    assert r.label == "within_baseline"  # a mood of 2 is not compared, so not flagged


def test_nothing_comparable_is_insufficient_even_with_history():
    history = steady(14)
    r = analyze_checkin(nxt(history, None, None, None), history)
    assert r.label == "insufficient_data"
    assert r.score is None
    assert "no indicator in this check-in could be compared" in r.explanation


def test_zero_spread_uses_floor():
    history = make_checkins([(6.0, 60.0, 4.0)] * 14)  # perfectly constant: MAD = 0
    small = analyze_checkin(nxt(history, 6.1, 61, 4), history)
    assert small.label == "within_baseline"
    assert small.details["indicators"]["sleep_duration_hours"]["spread"] == 0.25
    assert small.details["indicators"]["resting_heart_rate"]["spread"] == 2.0

    large = analyze_checkin(nxt(history, 6.0, 72, 4), history)
    assert large.label == "worth_reviewing"
    assert [c.feature for c in large.contributing_changes] == ["resting_heart_rate"]
    change = large.contributing_changes[0]
    assert (change.observed, change.baseline, change.unit) == (72.0, 60.0, "bpm")
    assert "Resting heart rate was 72 bpm, above your usual 60 bpm" in large.explanation


def test_trend_only_change_reports_last_3_average():
    # Two short nights, then a night only a little below usual: this check-in alone is
    # within 2 spreads, but the last-3 average is clearly below the usual median.
    history = make_checkins(steady_rows(12) + [(5.4, 60.0, 4.0), (5.3, 60.0, 4.0)])
    r = analyze_checkin(nxt(history, 6.1, 60, 4), history)
    sleep = r.details["indicators"]["sleep_duration_hours"]
    assert abs(sleep["deviation"]) < 2.0 and sleep["trend"] <= -1.5
    assert r.label == "worth_reviewing"
    [change] = r.contributing_changes
    assert change.feature == "sleep_duration_hours" and change.basis == "last_3_checkins"
    assert change.observed == round((6.1 + 5.3 + 5.4) / 3, 1)
    assert "Sleep averaged 5.6 h over your last 3 check-ins, below your usual" in r.explanation


def test_same_input_gives_same_score_twice_and_after_refit():
    history = steady(14)
    target = nxt(history, 5.0, 68, 3)
    first = analyze_checkin(target, history)
    second = analyze_checkin(target, history)
    reference_model.cache_clear()
    refit = analyze_checkin(target, history)
    assert first.score == second.score == refit.score
    assert first.label == second.label == refit.label
    assert first.explanation == refit.explanation


@pytest.mark.parametrize(
    "values",
    [(6.5, 60, 4), (4.0, 75, 1), (9.0, 50, 5), (None, 60, 4), (6.5, None, None)],
)
def test_explanations_avoid_diagnosis_words(values):
    history = steady(14)
    for r in (analyze_checkin(nxt(history, *values), history), analyze_checkin(None, [])):
        assert not FORBIDDEN.search(r.explanation), r.explanation
        assert "validated on astronaut medical data" in r.details["not_validated"]


def test_explanation_shows_the_same_baseline_as_contributing_changes():
    # Even count with a half-value median: 7 x 60 bpm and 7 x 61 bpm -> 60.5 bpm.
    history = make_checkins([(6.5, 60.0 + i % 2, 4.0) for i in range(14)])
    r = analyze_checkin(nxt(history, 6.5, 75, 4), history)
    [change] = r.contributing_changes
    assert change.baseline == 60.5
    assert "above your usual 60.5 bpm" in r.explanation
