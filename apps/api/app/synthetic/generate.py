"""Deterministic synthetic dataset for the Pulsar demo (docs/synthetic-data.md).

Usage (from apps/api):
    .venv/bin/python -m app.synthetic [--seed 2026] [--out app/synthetic/out]

Same seed → byte-identical files. Everything is simulated and labelled as such.
"""

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from app.synthetic.config import (
    DEFAULT_SEED,
    GENERATOR_VERSION,
    MISSION_DAYS,
    MISSION_LABEL,
    MISSION_START,
    SAMPLE_MINUTES,
    SCENARIOS,
)
from app.synthetic.crew import generate_crew
from app.synthetic.environment import generate_environment

DEFAULT_OUT = Path(__file__).parent / "out"

COLUMNS = {
    "crew_profiles": (
        "id",
        "user_id",
        "profile_code",
        "display_name",
        "mission_label",
        "baseline_metadata",
        "is_fictional",
    ),
    "health_checkins": (
        "id",
        "profile_id",
        "recorded_at",
        "sleep_duration_hours",
        "mood_rating",
        "resting_heart_rate",
        "source",
        "is_simulated",
        "data_quality",
    ),
    "environment_readings": (
        "id",
        "recorded_at",
        "source",
        "instrument",
        "measurement_type",
        "value",
        "unit",
        "location_context",
        "is_simulated",
        "is_stale",
        "source_retrieved_at",
        "metadata",
    ),
    "mission_events": (
        "id",
        "event_type",
        "level",
        "start_time",
        "end_time",
        "source",
        "source_event_id",
        "link",
        "is_simulated",
        "metadata",
    ),
}


@dataclass(frozen=True)
class Dataset:
    tables: dict[str, list[dict[str, Any]]]
    manifest: dict[str, Any]


def generate(seed: int = DEFAULT_SEED) -> Dataset:
    root = np.random.default_rng(seed)
    crew_rng, env_rng = root.spawn(2)
    profiles, checkins, crew_manifest = generate_crew(seed, crew_rng)
    readings, events, env_manifest = generate_environment(seed, env_rng)
    tables = {
        "crew_profiles": profiles,
        "health_checkins": checkins,
        "environment_readings": readings,
        "mission_events": events,
    }
    manifest = {
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "simulated": True,
        "notice": "Synthetic demo data. Not NASA or NOAA data. Not personal dose.",
        "mission": {
            "label": MISSION_LABEL,
            "start": _fmt(MISSION_START),
            "days": MISSION_DAYS,
            "environment_sample_minutes": SAMPLE_MINUTES,
        },
        "scenarios": [
            {
                "id": s.id,
                "target": s.target,
                "days": [s.first_day, s.last_day],
                "description": s.description,
                "expected": s.expected,
            }
            for s in SCENARIOS
        ],
        "profiles": crew_manifest,
        "environment": env_manifest,
        "row_counts": {name: len(rows) for name, rows in tables.items()},
    }
    return Dataset(tables, manifest)


def _fmt(value: Any) -> str:
    """Format one value for Postgres-compatible CSV (empty = NULL)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, dict | list):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)  # floats are pre-rounded; str() gives the shortest round-trip repr


def write(dataset: Dataset, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, rows in dataset.tables.items():
        path = out_dir / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(COLUMNS[name])
            for row in rows:
                writer.writerow([_fmt(row[c]) for c in COLUMNS[name]])
        written.append(path)
    path = out_dir / "synthetic_manifest.json"
    path.write_text(json.dumps(dataset.manifest, indent=2, sort_keys=True) + "\n", "utf-8")
    written.append(path)
    return written


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    dataset = generate(args.seed)
    for path in write(dataset, args.out):
        print(f"wrote {path}")
    print(json.dumps(dataset.manifest["row_counts"]))


if __name__ == "__main__":
    main()
