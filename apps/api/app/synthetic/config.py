"""Fixed mission frame, profiles and scenarios for the synthetic generator.

Spec: docs/synthetic-data.md (synth-0.2.0). Days are 1-indexed: day 1 starts at MISSION_START.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

GENERATOR_VERSION = "synth-0.2.0"
DEFAULT_SEED = 2026
MISSION_START = datetime(2026, 9, 1, tzinfo=UTC)
MISSION_DAYS = 60
MISSION_LABEL = "Pulsar Demo Mission (simulated)"
SAMPLE_MINUTES = 5  # environment cadence, matches GOES 5-minute averages
MOOD_SCALE = "pulsar-mood-1to5-v1"

# Stable namespace so the same seed always yields the same row ids.
ID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "urn:pulsar:synthetic")


def day_start(day: int) -> datetime:
    return MISSION_START + timedelta(days=day - 1)


def make_id(seed: int, *parts: object) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "/".join([GENERATOR_VERSION, str(seed), *map(str, parts)])))


@dataclass(frozen=True)
class Profile:
    code: str
    scenario_id: str
    first_day: int = 1
    last_day: int = MISSION_DAYS

    @property
    def display_name(self) -> str:
        return f"Crew {self.code.split('-')[1]} (fictional)"


PROFILES: tuple[Profile, ...] = (
    Profile("CREW-A", "S0_stable"),
    Profile("CREW-B", "S1_sleep_decline"),
    Profile("CREW-C", "S2_rhr_trend"),
    Profile("CREW-D", "S3_new_profile", first_day=56),
)


@dataclass(frozen=True)
class Scenario:
    id: str
    target: str  # profile code, "all" or "environment"
    first_day: int
    last_day: int
    description: str
    expected: str


SCENARIOS: tuple[Scenario, ...] = (
    Scenario("S0_stable", "CREW-A", 1, MISSION_DAYS, "Baseline only", "within_baseline"),
    Scenario(
        "S1_sleep_decline",
        "CREW-B",
        36,
        55,
        "Sleep drops linearly by 1.5 h over days 36-50, mood follows; recovers days 51-55",
        "worth_reviewing from about day 42 (sleep, mood)",
    ),
    Scenario(
        "S2_rhr_trend",
        "CREW-C",
        42,
        49,
        "Resting HR +1.5 bpm/day up to +10 bpm; sleep unchanged",
        "worth_reviewing (resting HR only)",
    ),
    Scenario("S3_new_profile", "CREW-D", 56, 60, "Only 5 days of check-ins", "insufficient_data"),
    Scenario("S4_schedule_shift", "all", 20, 21, "Sleep -1.0 h for everyone", "short dip"),
    Scenario(
        "S5_solar_storm",
        "environment",
        27,
        28,
        "Simulated S2 solar radiation storm + mission_events row",
        'space weather banner "S2 Moderate (simulated)"',
    ),
    Scenario(
        "S6_co2_excursion",
        "environment",
        12,
        12,
        "Simulated CO2 scrubber slowdown from 10:00",
        "ppco2_above_1h_limit for a few hours",
    ),
    Scenario(
        "S7_stale_feed",
        "environment",
        33,
        33,
        "6-hour telemetry gap 12:00-18:00; last reading before the gap marked stale",
        "freshness label demo",
    ),
)

# Crew-level scenario "key windows": no missing rows or null fields are placed inside them.
KEY_WINDOWS: dict[str, list[tuple[int, int]]] = {
    "CREW-A": [(20, 21)],
    "CREW-B": [(20, 21), (36, 55)],
    "CREW-C": [(20, 21), (42, 49)],
    "CREW-D": [(56, 60)],
}

# Missing-data rates (section 5).
MISSING_DAY_RATE = 0.06
NULL_FIELD_RATE = 0.02

# Environment scenario timing (hours from that day's 00:00 UTC).
S5_DAY, S5_START_H, S5_RISE_H, S5_PEAK_PFU, S5_EFOLD_H = 27, 6.0, 6.0, 180.0, 12.0
S6_DAY, S6_START_H, S6_RISE_H, S6_HOLD_H, S6_FALL_H, S6_PEAK_MMHG = 12, 10.0, 6.0, 2.0, 4.0, 4.0
S7_DAY, S7_START_H, S7_GAP_H = 33, 12.0, 6.0

LOCATION_ISS = "US Lab (simulated)"
LOCATION_GEO = "Geostationary orbit (GOES-like, simulated)"
