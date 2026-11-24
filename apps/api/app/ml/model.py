"""Isolation Forest over self-relative deviation features.

How it is fit: once per process, on a fixed reference set of feature vectors produced by
*steady* histories (independent standard-normal day-to-day noise for each indicator, windows
of 7 to 14 check-ins, scored by the same median/MAD/trend arithmetic as real data). Because
every feature is already relative to the person's own median and spread, "usual variation"
looks the same for everyone in this space, so one pooled reference serves every profile.

Why not fit per profile: a profile only has 7 to 14 baseline check-ins. A forest fit on that
few points isolates almost any point in ~3-4 splits, so its scores are close to arbitrary.
Personalisation lives in the features (median and spread of the person's own window); the
forest only judges how unusual the *combination* of deviations is.

The reference contains no scenario data and no environment data, and is fully deterministic.
"""

from functools import lru_cache

import numpy as np
from sklearn.ensemble import IsolationForest

from app.ml.features import (
    BASELINE_WINDOW,
    MIN_HISTORY,
    RECENT_CHECKINS,
    IndicatorFeatures,
    robust_spread,
)

REFERENCE_SEED = 20261124
REFERENCE_SIZE = 4000
FOREST_SEED = 7
# Floor on the reference spread, in standard-deviation units (mirrors the per-indicator
# measurement-resolution floors used on real data).
REFERENCE_SPREAD_FLOOR = 0.5
# A check-in is "outside usual variation" when its score is higher than this share of
# reference (steady) check-ins.
SCORE_QUANTILE = 0.925


def feature_vector(features: list[IndicatorFeatures]) -> np.ndarray:
    """[deviation x3, trend x3]; indicators that are left out contribute 0 (= at baseline)."""
    devs = [f.deviation if f.status == "used" else 0.0 for f in features]
    trends = [f.trend if f.status == "used" else 0.0 for f in features]
    return np.array(devs + trends, dtype=float)


def _reference_vectors(n_indicators: int) -> np.ndarray:
    rng = np.random.default_rng(REFERENCE_SEED)
    rows = np.empty((REFERENCE_SIZE, 2 * n_indicators))
    for r in range(REFERENCE_SIZE):
        length = int(rng.integers(MIN_HISTORY, BASELINE_WINDOW + 1))
        for i in range(n_indicators):
            x = rng.standard_normal(length + 1)
            window, observed = x[:-1], x[-1]
            median = np.median(window)
            spread = robust_spread(window, REFERENCE_SPREAD_FLOOR)
            recent = x[-RECENT_CHECKINS:].mean()
            rows[r, i] = (observed - median) / spread
            rows[r, n_indicators + i] = (recent - median) / spread
    return rows


@lru_cache(maxsize=1)
def reference_model(n_indicators: int = 3) -> tuple[IsolationForest, float]:
    """Return (fitted forest, score threshold). Cached; identical on every call and run."""
    reference = _reference_vectors(n_indicators)
    forest = IsolationForest(
        n_estimators=200, max_samples=256, random_state=FOREST_SEED, n_jobs=1
    ).fit(reference)
    threshold = float(np.quantile(anomaly_scores(forest, reference), SCORE_QUANTILE))
    return forest, threshold


def anomaly_scores(forest: IsolationForest, x: np.ndarray) -> np.ndarray:
    """Isolation Forest score in (0, 1): higher means more unusual (Liu et al. s(x, n))."""
    return -forest.score_samples(np.atleast_2d(x))


def score(features: list[IndicatorFeatures]) -> tuple[float, float]:
    """(score, threshold) for one check-in's features."""
    forest, threshold = reference_model(len(features))
    return float(anomaly_scores(forest, feature_vector(features))[0]), threshold
