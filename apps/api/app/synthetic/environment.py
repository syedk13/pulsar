"""Mission-context telemetry and events (docs/synthetic-data.md section 7).

Every series shares one 5-minute mission clock so it aligns with check-ins by timestamp.
These are simulated module/orbit readings, never a person's dose, and never model inputs.
"""

from typing import Any

import numpy as np

from app.limits import (
    PPCO2_1H_LIMIT_MMHG,
    PPCO2_ISS_RANGE_MMHG,
    S_SCALE_STORM_THRESHOLD_PFU,
    s_scale_label,
    s_scale_level,
)
from app.synthetic.config import (
    GENERATOR_VERSION,
    LOCATION_GEO,
    LOCATION_ISS,
    MISSION_DAYS,
    MISSION_START,
    S5_DAY,
    S5_EFOLD_H,
    S5_PEAK_PFU,
    S5_RISE_H,
    S5_START_H,
    S6_DAY,
    S6_FALL_H,
    S6_HOLD_H,
    S6_PEAK_MMHG,
    S6_RISE_H,
    S6_START_H,
    S7_DAY,
    S7_GAP_H,
    S7_START_H,
    SAMPLE_MINUTES,
    make_id,
)

MIN_PER_DAY = 24 * 60
N = MISSION_DAYS * MIN_PER_DAY // SAMPLE_MINUTES
SAMPLES_PER_HOUR = 60 // SAMPLE_MINUTES
H_PER_SAMPLE = SAMPLE_MINUTES / 60

ORBIT_MIN = 92.0
SAA_HALF_WIDTH_MIN = 7.5  # ~15-minute pass
DAILY_ABSORBED_TARGET_UGY = (150.0, 290.0)
CO2_EXERCISE_BLOCKS_H = ((9.0, 10.0), (16.0, 17.0))
PROTON_BG_MEDIAN_PFU = 0.3

SERIES = {
    # measurement_type: (unit, instrument, location, modeled_on, decimals)
    "absorbed_dose_rate": (
        "uGy/h",
        "sim-dosimeter",
        LOCATION_ISS,
        "OSDR RadLab dose-rate shape",
        3,
    ),
    "dose_equivalent_rate": (
        "uSv/h",
        "sim-dosimeter",
        LOCATION_ISS,
        "OSDR RadLab dose-rate shape",
        3,
    ),
    "acceleration_quasi_steady": (
        "micro-g",
        "sim-accelerometer",
        LOCATION_ISS,
        "NASA PIMS quasi-steady (MAMS) shape",
        3,
    ),
    "ppco2": ("mmHg", "sim-co2-monitor", LOCATION_ISS, "OCHMO-TB-004 ISS ppCO2 range", 3),
    "proton_flux_ge10mev": (
        "pfu",
        "sim-proton-monitor",
        LOCATION_GEO,
        "NOAA GOES >=10 MeV integral proton format",
        4,
    ),
}

t_min = np.arange(N) * SAMPLE_MINUTES  # minutes since mission start
t_h = t_min / 60.0
day_idx = t_min // MIN_PER_DAY  # 0-based
hour_of_day = (t_min % MIN_PER_DAY) / 60.0
TIMESTAMPS = np.datetime_as_string(
    np.datetime64(MISSION_START.replace(tzinfo=None), "m") + t_min.astype("timedelta64[m]"),
    unit="s",
)
TIMESTAMPS = np.char.add(TIMESTAMPS, "Z")


def _mission_hour(day: int, hour: float) -> float:
    return (day - 1) * 24 + hour


def trailing_mean(values: np.ndarray, window: int) -> np.ndarray:
    """Trailing mean over `window` samples (shorter at the very start)."""
    csum = np.concatenate([[0.0], np.cumsum(values)])
    idx = np.arange(1, len(values) + 1)
    lo = np.maximum(0, idx - window)
    return (csum[idx] - csum[lo]) / (idx - lo)


def _proton_flux(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    background = rng.lognormal(np.log(PROTON_BG_MEDIAN_PFU), 0.3, N)
    storm_noise = rng.lognormal(0.0, 0.1, N)
    t0 = _mission_hour(S5_DAY, S5_START_H)
    t_peak = t0 + S5_RISE_H
    storm = np.zeros(N)
    rise = (t_h >= t0) & (t_h < t_peak)
    log_lo, log_hi = np.log(PROTON_BG_MEDIAN_PFU), np.log(S5_PEAK_PFU)
    storm[rise] = np.exp(log_lo + (log_hi - log_lo) * (t_h[rise] - t0) / S5_RISE_H)
    decay = t_h >= t_peak
    storm[decay] = S5_PEAK_PFU * np.exp(-(t_h[decay] - t_peak) / S5_EFOLD_H)
    storm *= storm_noise
    is_event = storm > background
    return np.where(is_event, storm, background), is_event


def _radiation(
    rng: np.random.Generator, storm_mask: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    phase = rng.uniform(0, 2 * np.pi)
    background = 4.0 + 2.0 * np.sin(2 * np.pi * t_min / ORBIT_MIN + phase)
    background = np.where(storm_mask, background * 1.5, background)

    saa = np.zeros(N)
    saa_blocks = []
    for d in range(MISSION_DAYS):
        n_orbits = int(rng.integers(5, 7))
        start = float(rng.uniform(0, MIN_PER_DAY - n_orbits * ORBIT_MIN))
        peaks = rng.uniform(50, 300, n_orbits)
        for k in range(n_orbits):
            centre = d * MIN_PER_DAY + start + k * ORBIT_MIN + SAA_HALF_WIDTH_MIN
            saa += peaks[k] * np.clip(1 - np.abs(t_min - centre) / SAA_HALF_WIDTH_MIN, 0, None)
        saa_blocks.append({"day": d + 1, "orbits": n_orbits, "start_min": round(start, 1)})

    noise = rng.lognormal(0.0, 0.1, N)
    bg_n, saa_n = background * noise, saa * noise

    # Keep each day's absorbed total in the target band by scaling only that day's SAA peaks.
    scaled_days = {}
    lo, hi = DAILY_ABSORBED_TARGET_UGY
    for d in range(MISSION_DAYS):
        m = day_idx == d
        bg_tot = bg_n[m].sum() * H_PER_SAMPLE
        saa_tot = saa_n[m].sum() * H_PER_SAMPLE
        total = bg_tot + saa_tot
        if not lo <= total <= hi:
            factor = (float(np.clip(total, lo, hi)) - bg_tot) / saa_tot
            saa_n[m] *= factor
            scaled_days[str(d + 1)] = round(float(factor), 4)

    absorbed = bg_n + saa_n
    q_per_day = rng.uniform(2.0, 2.5, MISSION_DAYS)
    q = q_per_day[day_idx]
    component = np.where(saa_n > 0, "saa", np.where(storm_mask, "event", "background"))
    meta = {
        "orbit_phase_rad": round(float(phase), 4),
        "saa_blocks": saa_blocks,
        "saa_scaled_days": scaled_days,
        "quality_factor_per_day": [round(float(v), 4) for v in q_per_day],
    }
    return absorbed, absorbed * q, component, meta | {"_q": q}


def _acceleration(
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
    x = rng.normal(1.0, 0.2, N)
    y = rng.normal(0.0, 0.4, N)
    z = rng.normal(0.0, 0.4, N)
    vents = []
    vent_mask = np.zeros(N, dtype=bool)
    cursor = float(rng.uniform(1, 3)) * MIN_PER_DAY
    while cursor < N * SAMPLE_MINUTES:
        start = round(cursor / SAMPLE_MINUTES) * SAMPLE_MINUTES
        duration = int(rng.integers(2, 5)) * SAMPLE_MINUTES  # 10, 15 or 20 min
        amp = float(rng.uniform(3.0, 4.0))
        m = (t_min >= start) & (t_min < start + duration)
        y[m] += amp
        z[m] += amp
        vent_mask |= m
        vents.append(
            {
                "start": str(TIMESTAMPS[min(start // SAMPLE_MINUTES, N - 1)]),
                "minutes": duration,
                "yz_offset_micro_g": round(amp, 3),
            }
        )
        cursor += float(rng.uniform(2, 3)) * MIN_PER_DAY
    return x, y, z, vent_mask, vents


def co2_excursion_weight() -> np.ndarray:
    s = t_h - _mission_hour(S6_DAY, S6_START_H)
    w = np.zeros(N)
    rise = (s >= 0) & (s < S6_RISE_H)
    w[rise] = s[rise] / S6_RISE_H
    hold = (s >= S6_RISE_H) & (s < S6_RISE_H + S6_HOLD_H)
    w[hold] = 1.0
    fall_start = S6_RISE_H + S6_HOLD_H
    fall = (s >= fall_start) & (s < fall_start + S6_FALL_H)
    w[fall] = 1.0 - (s[fall] - fall_start) / S6_FALL_H
    return w


def _ppco2(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, float]:
    base = float(rng.uniform(1.8, 2.2))
    wake = (hour_of_day >= 7.0) & (hour_of_day < 21.5)
    pattern = base + np.where(wake, 0.3, -0.2)
    for a, b in CO2_EXERCISE_BLOCKS_H:
        pattern += np.where((hour_of_day >= a) & (hour_of_day < b), 0.2, 0.0)
    w = co2_excursion_weight()
    values = pattern + w * (S6_PEAK_MMHG - pattern) + rng.normal(0, 0.08, N)
    return np.clip(values, *PPCO2_ISS_RANGE_MMHG), w > 0, base


def _span_event(mask: np.ndarray) -> tuple[str, str]:
    idx = np.flatnonzero(mask)
    return str(TIMESTAMPS[idx[0]]), str(TIMESTAMPS[idx[-1]])


def generate_environment(
    seed: int, rng: np.random.Generator
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Return (environment_readings rows, mission_events rows, manifest section)."""
    rad_rng, acc_rng, co2_rng, proton_rng = rng.spawn(4)

    flux, flux_event = _proton_flux(proton_rng)
    flux = np.round(flux, SERIES["proton_flux_ge10mev"][4])
    storm_mask = flux >= S_SCALE_STORM_THRESHOLD_PFU
    absorbed, dose_eq, rad_component, rad_meta = _radiation(rad_rng, storm_mask)
    q = rad_meta.pop("_q")
    ax, ay, az, vent_mask, vents = _acceleration(acc_rng)
    accel = np.sqrt(ax**2 + ay**2 + az**2)
    ppco2, co2_excursion, co2_base = _ppco2(co2_rng)

    values = {
        "absorbed_dose_rate": np.round(absorbed, 3),
        "dose_equivalent_rate": np.round(dose_eq, 3),
        "acceleration_quasi_steady": np.round(accel, 3),
        "ppco2": np.round(ppco2, 3),
        "proton_flux_ge10mev": flux,
    }
    components = {
        "absorbed_dose_rate": rad_component,
        "dose_equivalent_rate": rad_component,
        "acceleration_quasi_steady": np.where(vent_mask, "event", "nominal"),
        "ppco2": np.where(co2_excursion, "excursion", "nominal"),
        "proton_flux_ge10mev": np.where(flux_event, "event", "background"),
    }

    # Events: derived from the generated values with the same rules live data will use.
    events = []
    storm_start, storm_end = _span_event(storm_mask)
    level = s_scale_level(float(flux.max()))
    assert level is not None
    events.append(
        {
            "id": make_id(seed, "mission_events", "S5_solar_storm"),
            "event_type": "S_SCALE",
            "level": level,
            "start_time": storm_start,
            "end_time": storm_end,
            "source": "synthetic",
            "source_event_id": None,
            "link": None,
            "is_simulated": True,
            "metadata": {
                "generator_version": GENERATOR_VERSION,
                "scenario_id": "S5_solar_storm",
                "label": f"{level} {s_scale_label(level)} (simulated)",
                "peak_flux_pfu": float(flux.max()),
                "location_context": LOCATION_GEO,
            },
        }
    )
    co2_1h = trailing_mean(values["ppco2"], SAMPLES_PER_HOUR)
    over = co2_1h > PPCO2_1H_LIMIT_MMHG
    co2_start, co2_end = _span_event(over)
    events.append(
        {
            "id": make_id(seed, "mission_events", "S6_co2_excursion"),
            "event_type": "CO2_EXCURSION",
            "level": "ppco2_above_1h_limit",
            "start_time": co2_start,
            "end_time": co2_end,
            "source": "synthetic",
            "source_event_id": None,
            "link": None,
            "is_simulated": True,
            "metadata": {
                "generator_version": GENERATOR_VERSION,
                "scenario_id": "S6_co2_excursion",
                "peak_1h_mean_mmhg": round(float(co2_1h.max()), 3),
                "limit_mmhg": PPCO2_1H_LIMIT_MMHG,
                "limit_source": "NASA-STD-3001 V2 6004",
                "location_context": LOCATION_ISS,
            },
        }
    )

    # S7: drop a 6-hour window from every series; mark the last pre-gap reading stale.
    gap_lo = _mission_hour(S7_DAY, S7_START_H)
    gap = (t_h >= gap_lo) & (t_h < gap_lo + S7_GAP_H)
    gap_idx = np.flatnonzero(gap)
    stale_i = int(gap_idx[0]) - 1
    gap_until = str(TIMESTAMPS[gap_idx[-1] + 1])
    keep = np.flatnonzero(~gap)

    readings: list[dict[str, Any]] = []
    for mtype, (unit, instrument, location, modeled_on, _dec) in SERIES.items():
        vals, comps = values[mtype], components[mtype]
        for i in keep.tolist():
            ts = str(TIMESTAMPS[i])
            meta: dict[str, Any] = {
                "generator_version": GENERATOR_VERSION,
                "modeled_on": modeled_on,
                "component": str(comps[i]),
            }
            if mtype == "dose_equivalent_rate":
                meta["quality_factor"] = round(float(q[i]), 4)
            elif mtype == "acceleration_quasi_steady":
                meta["axes"] = {
                    "x": round(float(ax[i]), 3),
                    "y": round(float(ay[i]), 3),
                    "z": round(float(az[i]), 3),
                }
                meta["band"] = "<0.01 Hz"
            is_stale = i == stale_i
            if is_stale:
                meta["scenario_id"] = "S7_stale_feed"
                meta["feed_gap_until"] = gap_until
            readings.append(
                {
                    "id": make_id(seed, "environment_readings", mtype, ts),
                    "recorded_at": ts,
                    "source": "synthetic",
                    "instrument": instrument,
                    "measurement_type": mtype,
                    "value": float(vals[i]),
                    "unit": unit,
                    "location_context": location,
                    "is_simulated": True,
                    "is_stale": is_stale,
                    "source_retrieved_at": ts,
                    "metadata": meta,
                }
            )

    daily_abs = np.bincount(day_idx, weights=values["absorbed_dose_rate"]) * H_PER_SAMPLE
    daily_deq_msv = (
        np.bincount(day_idx, weights=values["dose_equivalent_rate"]) * H_PER_SAMPLE / 1000
    )
    manifest = {
        "radiation": rad_meta
        | {
            "daily_absorbed_ugy": [round(float(v), 2) for v in daily_abs],
            "daily_dose_equivalent_msv": [round(float(v), 4) for v in daily_deq_msv],
        },
        "acceleration": {"venting_transients": vents},
        "ppco2": {
            "mission_baseline_mmhg": round(co2_base, 4),
            "exercise_blocks_utc_h": [list(b) for b in CO2_EXERCISE_BLOCKS_H],
        },
        "proton_flux": {"background_median_pfu": PROTON_BG_MEDIAN_PFU},
        "stale_feed": {
            "gap_start": str(TIMESTAMPS[gap_idx[0]]),
            "gap_end_exclusive": gap_until,
            "stale_reading_at": str(TIMESTAMPS[stale_i]),
            "series": list(SERIES),
        },
    }
    return readings, events, manifest
