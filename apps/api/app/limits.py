"""Official environment reference values used by Pulsar (docs/synthetic-data.md section 2).

Environment context only. None of these are crew health thresholds and none may be used
to explain a crew member's flag. Shared by the synthetic generator and future live-mode
providers so both derive labels the same way.
"""

# NASA-STD-3001 Vol 2 Rev D, V2 6004: cabin ppCO2 1-hour mean must stay at or below this.
PPCO2_1H_LIMIT_MMHG = 3.0
# OCHMO-TB-004 guidance (not a requirement): 7-day mean below this keeps headache risk < 1%.
PPCO2_7D_GUIDANCE_MMHG = 2.5
# OCHMO-TB-004 historical ISS ppCO2 range, used only as a generator bound.
PPCO2_ISS_RANGE_MMHG = (1.0, 9.0)

# NASA-STD-3001 Vol 1 Rev C, V1 4033: GCR design dose rate in free space. A vehicle design
# value in effective dose. Pulsar uses it ONLY as a sanity ceiling on generated data.
V1_4033_GCR_FREE_SPACE_MSV_PER_DAY = 1.3

# NOAA space weather S-scale: >=10 MeV integral proton flux (pfu) at geostationary orbit.
S_SCALE_THRESHOLDS_PFU: tuple[tuple[str, str, float], ...] = (
    ("S5", "Extreme", 100_000.0),
    ("S4", "Severe", 10_000.0),
    ("S3", "Strong", 1_000.0),
    ("S2", "Moderate", 100.0),
    ("S1", "Minor", 10.0),
)
S_SCALE_STORM_THRESHOLD_PFU = 10.0


def s_scale_level(flux_pfu: float) -> str | None:
    """Return the NOAA S-level ("S1".."S5") for a >=10 MeV flux, or None below S1."""
    for level, _label, threshold in S_SCALE_THRESHOLDS_PFU:
        if flux_pfu >= threshold:
            return level
    return None


def s_scale_label(level: str) -> str:
    for lvl, label, _threshold in S_SCALE_THRESHOLDS_PFU:
        if lvl == level:
            return label
    raise ValueError(f"unknown S-level: {level}")
