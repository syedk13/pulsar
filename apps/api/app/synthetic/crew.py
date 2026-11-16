"""Fictional crew profiles and daily check-ins (docs/synthetic-data.md sections 5 and 6)."""

from datetime import timedelta
from typing import Any

import numpy as np

from app.synthetic.config import (
    GENERATOR_VERSION,
    KEY_WINDOWS,
    MISSING_DAY_RATE,
    MISSION_DAYS,
    MISSION_LABEL,
    MOOD_SCALE,
    NULL_FIELD_RATE,
    PROFILES,
    SCENARIOS,
    Profile,
    day_start,
    make_id,
)

DAYS = np.arange(1, MISSION_DAYS + 1)
CHECKIN_FIELDS = ("sleep_duration_hours", "resting_heart_rate", "mood_rating")

# Demo assumption beyond the sleep→mood coupling so S1's mood change is visible:
# extra latent-mood offset at the deepest point of the sleep decline.
S1_MOOD_EXTRA = -0.5
S1_SLEEP_DROP_H = 1.5
S2_RHR_SLOPE, S2_RHR_CAP = 1.5, 10.0
S4_SLEEP_DROP_H = 1.0

_SCENARIO_WINDOWS = {s.id: (s.first_day, s.last_day) for s in SCENARIOS}


def _in(day: int, window: tuple[int, int]) -> bool:
    return window[0] <= day <= window[1]


def s1_sleep_offset(day: int) -> float:
    if 36 <= day <= 50:
        return -S1_SLEEP_DROP_H * (day - 36) / (50 - 36)
    if 51 <= day <= 55:
        return -S1_SLEEP_DROP_H * (55 - day) / (55 - 50)
    return 0.0


def s2_rhr_offset(day: int) -> float:
    if 42 <= day <= 49:
        return min(S2_RHR_CAP, S2_RHR_SLOPE * (day - 41))
    return 0.0


def scenario_for(profile: Profile, day: int) -> str:
    own = _SCENARIO_WINDOWS[profile.scenario_id]
    if profile.scenario_id != "S0_stable" and _in(day, own):
        return profile.scenario_id
    if _in(day, _SCENARIO_WINDOWS["S4_schedule_shift"]):
        return "S4_schedule_shift"
    return "S0_stable"


def _offsets(profile: Profile, day: int) -> tuple[float, float, float]:
    """(sleep h, resting HR bpm, latent mood) scenario offsets for one profile-day."""
    sleep = rhr = mood = 0.0
    if _in(day, _SCENARIO_WINDOWS["S4_schedule_shift"]):
        sleep -= S4_SLEEP_DROP_H
    if profile.scenario_id == "S1_sleep_decline":
        s1 = s1_sleep_offset(day)
        sleep += s1
        mood += S1_MOOD_EXTRA * (s1 / -S1_SLEEP_DROP_H)
    if profile.scenario_id == "S2_rhr_trend":
        rhr += s2_rhr_offset(day)
    return sleep, rhr, mood


def _in_key_window(code: str, day: int) -> bool:
    return any(_in(day, w) for w in KEY_WINDOWS[code])


def generate_crew(
    seed: int, rng: np.random.Generator
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Return (crew_profiles rows, health_checkins rows, manifest section)."""
    profile_rngs = rng.spawn(len(PROFILES))
    profiles_out: list[dict[str, Any]] = []
    checkins_out: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {}

    for profile, prng in zip(PROFILES, profile_rngs, strict=True):
        param_rng, noise_rng, gap_rng = prng.spawn(3)
        sleep_base = float(param_rng.uniform(5.6, 7.0))
        rhr_base = float(param_rng.uniform(52, 66))
        mood_base = float(param_rng.uniform(3.4, 4.2))

        # Draw noise for every mission day so a profile's stream never depends on its range.
        sleep_noise = noise_rng.normal(0, 0.6, MISSION_DAYS)
        rhr_noise = noise_rng.normal(0, 2.5, MISSION_DAYS)
        mood_noise = noise_rng.normal(0, 0.5, MISSION_DAYS)
        jitter_s = noise_rng.uniform(-30 * 60, 30 * 60, MISSION_DAYS)

        profile_id = make_id(seed, "crew_profiles", profile.code)
        profiles_out.append(
            {
                "id": profile_id,
                "user_id": None,
                "profile_code": profile.code,
                "display_name": profile.display_name,
                "mission_label": MISSION_LABEL,
                "baseline_metadata": {},
                "is_fictional": True,
            }
        )

        days = [d for d in DAYS.tolist() if profile.first_day <= d <= profile.last_day]
        eligible = [d for d in days if not _in_key_window(profile.code, d)]
        n_missing = min(len(eligible), round(MISSING_DAY_RATE * len(days)))
        missing_days = sorted(gap_rng.choice(eligible, size=n_missing, replace=False).tolist())
        present = [d for d in days if d not in missing_days]
        eligible_rows = [d for d in present if not _in_key_window(profile.code, d)]
        n_null = min(len(eligible_rows), round(NULL_FIELD_RATE * len(present)))
        null_days = gap_rng.choice(eligible_rows, size=n_null, replace=False).tolist()
        null_fields = {
            int(d): CHECKIN_FIELDS[int(gap_rng.integers(len(CHECKIN_FIELDS)))] for d in null_days
        }

        for day in present:
            i = day - 1
            sleep_off, rhr_off, mood_off = _offsets(profile, day)
            sleep_true = sleep_base + sleep_noise[i] + sleep_off
            sleep = float(np.clip(round(sleep_true, 1), 3.0, 9.5))
            deficit = max(0.0, sleep_base - sleep)
            rhr = int(np.clip(round(rhr_base + rhr_noise[i] + rhr_off + 1.0 * deficit), 40, 110))
            latent = mood_base + mood_noise[i] + mood_off + 0.3 * (sleep - sleep_base)
            mood = int(np.clip(round(latent), 1, 5))

            values: dict[str, Any] = {
                "sleep_duration_hours": sleep,
                "resting_heart_rate": rhr,
                "mood_rating": mood,
            }
            missing_fields = []
            if day in null_fields:
                values[null_fields[day]] = None
                missing_fields.append(null_fields[day])

            recorded_at = day_start(day) + timedelta(hours=7, seconds=round(float(jitter_s[i])))
            checkins_out.append(
                {
                    "id": make_id(seed, "health_checkins", profile.code, day),
                    "profile_id": profile_id,
                    "recorded_at": recorded_at,
                    **values,
                    "source": "synthetic",
                    "is_simulated": True,
                    "data_quality": {
                        "generator_version": GENERATOR_VERSION,
                        "scenario_id": scenario_for(profile, day),
                        "hr_kind": "resting_morning",
                        "mood_scale": MOOD_SCALE,
                        "missing_fields": missing_fields,
                        "mission_day": day,
                    },
                }
            )

        manifest[profile.code] = {
            "profile_id": profile_id,
            "scenario_id": profile.scenario_id,
            "days": [profile.first_day, profile.last_day],
            "true_baseline": {
                "sleep_duration_hours": round(sleep_base, 3),
                "resting_heart_rate": round(rhr_base, 3),
                "mood_latent": round(mood_base, 3),
            },
            "missing_days": missing_days,
            "null_fields": {str(d): f for d, f in sorted(null_fields.items())},
            "checkin_count": len(present),
        }

    return profiles_out, checkins_out, manifest
