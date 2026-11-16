"""Checks required by docs/synthetic-data.md sections 7a, 7c and 10."""

from pathlib import Path

import pandas as pd
import pytest

from app.limits import (
    PPCO2_1H_LIMIT_MMHG,
    PPCO2_7D_GUIDANCE_MMHG,
    V1_4033_GCR_FREE_SPACE_MSV_PER_DAY,
    s_scale_level,
)
from app.synthetic import generate, write
from app.synthetic.config import DEFAULT_SEED, KEY_WINDOWS, MISSION_DAYS


@pytest.fixture(scope="module")
def dataset():
    return generate(DEFAULT_SEED)


@pytest.fixture(scope="module")
def env(dataset) -> pd.DataFrame:
    df = pd.DataFrame(dataset.tables["environment_readings"])
    df["t"] = pd.to_datetime(df["recorded_at"])
    return df


@pytest.fixture(scope="module")
def checkins(dataset) -> pd.DataFrame:
    df = pd.DataFrame(dataset.tables["health_checkins"])
    codes = {p["id"]: p["profile_code"] for p in dataset.tables["crew_profiles"]}
    df["code"] = df["profile_id"].map(codes)
    df["day"] = df["data_quality"].map(lambda q: q["mission_day"])
    return df


def _series(env: pd.DataFrame, mtype: str) -> pd.Series:
    s = env[env["measurement_type"] == mtype].set_index("t")["value"]
    return s.sort_index()


def test_same_seed_is_byte_identical(tmp_path: Path):
    a, b = tmp_path / "a", tmp_path / "b"
    write(generate(DEFAULT_SEED), a)
    write(generate(DEFAULT_SEED), b)
    files = sorted(p.name for p in a.iterdir())
    assert files == sorted(p.name for p in b.iterdir())
    for name in files:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_different_seed_differs(dataset):
    other = generate(DEFAULT_SEED + 1)
    assert other.tables["health_checkins"] != dataset.tables["health_checkins"]


def test_row_counts(dataset):
    counts = dataset.manifest["row_counts"]
    assert counts["crew_profiles"] == 4
    assert counts["mission_events"] == 2
    # 5 series x 17,280 five-minute samples, minus the 6-hour S7 gap (72 samples each).
    assert counts["environment_readings"] == 5 * (17_280 - 72)
    assert 160 <= counts["health_checkins"] <= 185


def test_everything_labelled_simulated(dataset):
    for name in ("health_checkins", "environment_readings", "mission_events"):
        for row in dataset.tables[name]:
            assert row["source"] == "synthetic"
            assert row["is_simulated"] is True
    assert all(p["is_fictional"] for p in dataset.tables["crew_profiles"])
    assert all(p["baseline_metadata"] == {} for p in dataset.tables["crew_profiles"])


def test_v1_4033_guardrail(env):
    """Daily module dose-equivalent total stays well under 1.3 mSv/day (generator sanity)."""
    deq = _series(env, "dose_equivalent_rate")
    daily_msv = deq.resample("1D").sum() * (5 / 60) / 1000
    assert daily_msv.max() < V1_4033_GCR_FREE_SPACE_MSV_PER_DAY
    assert daily_msv.max() <= 0.75


def test_daily_absorbed_in_target_band(dataset):
    daily = dataset.manifest["environment"]["radiation"]["daily_absorbed_ugy"]
    assert len(daily) == MISSION_DAYS
    assert all(150 <= v <= 290 for v in daily)


def test_ppco2_1h_limit_only_during_s6(env):
    co2 = _series(env, "ppco2")
    mean_1h = co2.rolling("1h").mean()
    s6 = (mean_1h.index >= "2026-09-12T10:00Z") & (mean_1h.index < "2026-09-12T23:00Z")
    assert mean_1h[~s6].max() <= PPCO2_1H_LIMIT_MMHG
    assert mean_1h[s6].max() > PPCO2_1H_LIMIT_MMHG


def test_ppco2_7d_mean_below_guidance(env):
    mean_7d = _series(env, "ppco2").rolling("7D").mean()
    assert mean_7d.max() < PPCO2_7D_GUIDANCE_MMHG


def test_series_share_one_clock(env):
    stamps = env.groupby("measurement_type")["recorded_at"].apply(frozenset)
    assert stamps.nunique() == 1


def test_s5_storm_event(dataset, env):
    storm = next(e for e in dataset.tables["mission_events"] if e["event_type"] == "S_SCALE")
    assert storm["level"] == "S2"
    assert storm["metadata"]["label"] == "S2 Moderate (simulated)"
    assert storm["start_time"].startswith("2026-09-27")
    assert storm["end_time"].startswith("2026-09-28")
    flux = _series(env, "proton_flux_ge10mev")
    assert flux[flux.index < "2026-09-27"].max() < 10
    assert flux[flux.index >= "2026-09-29"].max() < 10


def test_s7_stale_feed(env):
    stale = env[env["is_stale"]]
    assert len(stale) == 5 and set(stale["recorded_at"]) == {"2026-10-03T11:55:00Z"}
    gap = (env["t"] >= "2026-10-03T12:00Z") & (env["t"] < "2026-10-03T18:00Z")
    assert not gap.any()


def test_no_missing_data_in_key_windows(checkins):
    for code, windows in KEY_WINDOWS.items():
        rows = checkins[checkins["code"] == code]
        for lo, hi in windows:
            in_window = rows[rows["day"].between(lo, hi)]
            assert sorted(in_window["day"]) == list(range(lo, hi + 1)), (code, lo, hi)
            assert all(not q["missing_fields"] for q in in_window["data_quality"])


def test_s1_sleep_decline(dataset, checkins):
    base = dataset.manifest["profiles"]["CREW-B"]["true_baseline"]["sleep_duration_hours"]
    late = checkins[(checkins["code"] == "CREW-B") & checkins["day"].between(46, 50)]
    assert late["sleep_duration_hours"].mean() < base - 0.8
    early = checkins[(checkins["code"] == "CREW-B") & (checkins["day"] < 36)]
    assert late["mood_rating"].mean() < early["mood_rating"].mean()


def test_s2_rhr_trend(dataset, checkins):
    base = dataset.manifest["profiles"]["CREW-C"]["true_baseline"]["resting_heart_rate"]
    late = checkins[(checkins["code"] == "CREW-C") & checkins["day"].between(47, 49)]
    assert late["resting_heart_rate"].mean() > base + 6


def test_s3_new_profile_has_five_days(checkins):
    assert sorted(checkins[checkins["code"] == "CREW-D"]["day"]) == [56, 57, 58, 59, 60]


@pytest.mark.parametrize(
    ("flux", "level"),
    [(9.99, None), (10, "S1"), (99.9, "S1"), (100, "S2"), (1e3, "S3"), (1e5, "S5")],
)
def test_s_scale_level(flux, level):
    assert s_scale_level(flux) == level
