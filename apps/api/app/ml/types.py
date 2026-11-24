"""Domain types for personal-baseline analysis. Pure data, no I/O."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Label = Literal["within_baseline", "worth_reviewing", "insufficient_data"]
IndicatorField = Literal["sleep_duration_hours", "resting_heart_rate", "mood_rating"]


@dataclass(frozen=True)
class Checkin:
    """One health check-in. A field is None when it was not recorded (never treated as 0)."""

    id: str
    recorded_at: datetime
    sleep_duration_hours: float | None
    resting_heart_rate: float | None
    mood_rating: float | None

    def value(self, field: IndicatorField) -> float | None:
        return getattr(self, field)


@dataclass(frozen=True)
class IndicatorSpec:
    field: IndicatorField
    name: str  # plain-language name used in explanations
    unit: str
    # Smallest spread used when scaling deviations. These are measurement-resolution floors
    # (so a perfectly steady history cannot turn a tiny change into a huge deviation),
    # not health thresholds.
    spread_floor: float
    decimals: int


INDICATORS: tuple[IndicatorSpec, ...] = (
    IndicatorSpec("sleep_duration_hours", "sleep", "h", spread_floor=0.25, decimals=1),
    IndicatorSpec("resting_heart_rate", "resting heart rate", "bpm", spread_floor=2.0, decimals=0),
    IndicatorSpec("mood_rating", "mood", "score (1-5)", spread_floor=0.75, decimals=1),
)
