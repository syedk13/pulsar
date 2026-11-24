"""Analyse one check-in against the person's own recent history. Pure function, no I/O.

Label rule (plain terms):
- insufficient_data ("collecting baseline"): fewer than MIN_HISTORY earlier check-ins, or no
  indicator could be compared (not recorded, or fewer than MIN_INDICATOR_VALUES values).
- worth_reviewing: at least one indicator differs from the person's usual (this check-in is
  >= DEVIATION_CHANGE spreads from the median, or the average of the last RECENT_CHECKINS
  check-ins is >= TREND_CHANGE spreads from it), AND either
    (a) the Isolation Forest finds the combination unusual: score above the gate (more
        unusual than SCORE_QUANTILE of steady reference check-ins), or
    (b) one indicator changed very clearly on its own (>= CLEAR_DEVIATION spreads, or a
        last-3 average >= CLEAR_TREND spreads). Needed because an axis-parallel forest over
        6 features scores a large change in a single feature only ~0.46, below the gate.
  The indicators meeting the first condition are the contributing changes, so every flag
  names what changed.
- within_baseline: otherwise.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.ml.explain import explain
from app.ml.features import (
    BASELINE_WINDOW,
    MIN_HISTORY,
    MIN_INDICATOR_VALUES,
    RECENT_CHECKINS,
    IndicatorFeatures,
    baseline_window,
    indicator_features,
)
from app.ml.model import SCORE_QUANTILE, score
from app.ml.types import INDICATORS, Checkin, Label

MODEL_VERSION = "baseline-iforest-0.1.0"
DEVIATION_CHANGE = 2.0  # spreads from the personal median, this check-in
TREND_CHANGE = 1.5  # spreads from the personal median, average of the last 3 check-ins
CLEAR_DEVIATION = 3.5  # a single indicator this far out is flagged without the forest gate
CLEAR_TREND = 3.0


@dataclass(frozen=True)
class ContributingChange:
    feature: str
    observed: float
    baseline: float
    unit: str
    basis: str  # "this_checkin" or "last_3_checkins"


@dataclass(frozen=True)
class AnalysisResult:
    label: Label
    score: float | None
    explanation: str
    contributing_changes: list[ContributingChange]
    model_version: str
    checkin_id: str | None
    details: dict[str, Any] = field(default_factory=dict)  # stored in anomaly_results.explanation


def _round(value: float | None, decimals: int) -> float | None:
    return None if value is None else round(value, max(decimals, 1))


def _changes(features: list[IndicatorFeatures]) -> list[ContributingChange]:
    out = []
    ranked = sorted(
        (f for f in features if f.status == "used"),
        key=lambda f: max(abs(f.deviation) / DEVIATION_CHANGE, abs(f.trend) / TREND_CHANGE),
        reverse=True,
    )
    for f in ranked:
        assert f.baseline is not None and f.observed is not None and f.recent_mean is not None
        d = f.spec.decimals
        if abs(f.deviation) >= DEVIATION_CHANGE:
            out.append(
                ContributingChange(
                    f.spec.field,
                    _round(f.observed, d),
                    _round(f.baseline, d),
                    f.spec.unit,
                    "this_checkin",
                )
            )
        elif abs(f.trend) >= TREND_CHANGE:
            out.append(
                ContributingChange(
                    f.spec.field,
                    _round(f.recent_mean, d),
                    _round(f.baseline, d),
                    f.spec.unit,
                    "last_3_checkins",
                )
            )
    return out


def _details(
    target: Checkin | None,
    window: Sequence[Checkin],
    features: list[IndicatorFeatures],
    threshold: float | None,
) -> dict[str, Any]:
    return {
        "scored_checkin": None
        if target is None
        else {"id": target.id, "recorded_at": target.recorded_at.isoformat()},
        "window": {
            "rule": f"median of the last {BASELINE_WINDOW} check-ins before this one, all sources",
            "baseline_checkins": len(window),
            "from": window[0].recorded_at.isoformat() if window else None,
            "to": window[-1].recorded_at.isoformat() if window else None,
            "min_checkins": MIN_HISTORY,
            "min_values_per_indicator": MIN_INDICATOR_VALUES,
            "recent_checkins_for_trend": RECENT_CHECKINS,
        },
        "indicators": {
            f.spec.field: {
                "status": f.status,
                "values_in_window": f.n_values,
                "observed": f.observed,
                "baseline": f.baseline,
                "spread": None if f.spread is None else round(f.spread, 4),
                "deviation": round(f.deviation, 4),
                "trend": round(f.trend, 4),
                "unit": f.spec.unit,
            }
            for f in features
        },
        "label_rule": {
            "score_gate_quantile": SCORE_QUANTILE,
            "score_threshold": None if threshold is None else round(threshold, 6),
            "deviation_change": DEVIATION_CHANGE,
            "trend_change": TREND_CHANGE,
            "clear_deviation": CLEAR_DEVIATION,
            "clear_trend": CLEAR_TREND,
        },
        "not_validated": "Not trained or validated on astronaut medical data.",
    }


def analyze_checkin(target: Checkin | None, earlier: Sequence[Checkin]) -> AnalysisResult:
    """Analyse `target` against `earlier` (all of the profile's check-ins before it, oldest
    first). `target=None` means the profile has no check-ins yet."""
    window = baseline_window(earlier)

    def result(label: Label, s: float | None, feats, changes, thr) -> AnalysisResult:
        text = explain(
            label, feats, changes, window, n_earlier=len(earlier), has_target=bool(target)
        )
        details = _details(target, window, feats, thr)
        details["text"] = text
        details["contributing_changes"] = [c.__dict__ for c in changes]
        return AnalysisResult(
            label=label,
            score=s,
            explanation=text,
            contributing_changes=changes,
            model_version=MODEL_VERSION,
            checkin_id=None if target is None else target.id,
            details=details,
        )

    if target is None or len(earlier) < MIN_HISTORY:
        return result("insufficient_data", None, [], [], None)

    features = [indicator_features(spec, target, window) for spec in INDICATORS]
    if not any(f.status == "used" for f in features):
        return result("insufficient_data", None, features, [], None)

    s, threshold = score(features)
    changes = _changes(features)
    clear = any(
        abs(f.deviation) >= CLEAR_DEVIATION or abs(f.trend) >= CLEAR_TREND
        for f in features
        if f.status == "used"
    )
    flagged = bool(changes) and (s >= threshold or clear)
    label: Label = "worth_reviewing" if flagged else "within_baseline"
    out = result(label, round(s, 6), features, changes if flagged else [], threshold)
    out.details["flag_path"] = (
        None if not flagged else "combination" if s >= threshold else "single_indicator"
    )
    return out
