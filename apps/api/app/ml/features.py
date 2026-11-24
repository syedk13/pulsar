"""Personal baseline and self-relative features per indicator. Pure functions."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np

from app.ml.types import Checkin, IndicatorSpec

BASELINE_WINDOW = 14  # last N earlier check-ins (count-based, all sources)
MIN_HISTORY = 7  # fewer earlier check-ins -> insufficient_data
MIN_INDICATOR_VALUES = 7  # fewer non-null values for one indicator -> that indicator is left out
RECENT_CHECKINS = 3  # scored check-in + 2 before it, for the short-term trend
MAD_TO_SD = 1.4826  # makes the MAD comparable to a standard deviation for normal noise

IndicatorStatus = Literal["used", "not_recorded", "short_history"]


@dataclass(frozen=True)
class IndicatorFeatures:
    spec: IndicatorSpec
    status: IndicatorStatus
    n_values: int  # non-null values in the baseline window
    observed: float | None = None
    baseline: float | None = None  # median of the window
    spread: float | None = None  # robust spread (scaled MAD, floored)
    deviation: float = 0.0  # (observed - baseline) / spread
    trend: float = 0.0  # (mean of recent values - baseline) / spread
    recent_mean: float | None = None


# Small-sample consistency factors for the MAD (Croux & Rousseeuw 1992): with only 7 to 14
# values the plain scaled MAD underestimates the spread, which would make ordinary days look
# unusual. Tabulated for n <= 9, n / (n - 0.8) above.
_MAD_SMALL_SAMPLE = {7: 1.140, 8: 1.129, 9: 1.107}


def mad_correction(n: int) -> float:
    return _MAD_SMALL_SAMPLE.get(n, n / (n - 0.8))


def robust_spread(values: np.ndarray, floor: float) -> float:
    """Scaled, small-sample-corrected MAD, never below `floor`."""
    mad = float(np.median(np.abs(values - np.median(values))))
    return max(MAD_TO_SD * mad_correction(len(values)) * mad, floor)


def baseline_window(earlier: Sequence[Checkin]) -> list[Checkin]:
    """The last BASELINE_WINDOW check-ins before the scored one (earlier is oldest first)."""
    return list(earlier[-BASELINE_WINDOW:])


def indicator_features(
    spec: IndicatorSpec, target: Checkin, window: Sequence[Checkin]
) -> IndicatorFeatures:
    values = np.array([v for c in window if (v := c.value(spec.field)) is not None], dtype=float)
    observed = target.value(spec.field)
    if observed is None:
        return IndicatorFeatures(spec, "not_recorded", len(values))
    if len(values) < MIN_INDICATOR_VALUES:
        return IndicatorFeatures(spec, "short_history", len(values), observed=float(observed))

    baseline = float(np.median(values))
    spread = robust_spread(values, spec.spread_floor)
    recent = [float(observed)]
    for c in reversed(window):
        if len(recent) == RECENT_CHECKINS:
            break
        if (v := c.value(spec.field)) is not None:
            recent.append(float(v))
    recent_mean = float(np.mean(recent))
    return IndicatorFeatures(
        spec,
        "used",
        len(values),
        observed=float(observed),
        baseline=baseline,
        spread=spread,
        deviation=(float(observed) - baseline) / spread,
        trend=(recent_mean - baseline) / spread,
        recent_mean=recent_mean,
    )
