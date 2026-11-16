# Data model

> Status: schema defined in `supabase/migrations/` (`20261114000000_initial_schema.sql`, then `20261116000000_environment_types_and_mission_events.sql`). Synthetic data loads with `supabase/load_synthetic.psql`.

All tables use `uuid` primary keys (`gen_random_uuid()`) and `timestamptz` timestamps. RLS is enabled on all tables.

## crew_profiles
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid → auth.users, unique, nullable | Only if Supabase Auth accounts are enabled |
| profile_code | text unique | Fictional identifier, e.g. `CREW-A` |
| display_name | text | |
| mission_label | text | |
| baseline_metadata | jsonb | Placeholder for future personal baselines |
| is_fictional | boolean (default true) | |
| created_at / updated_at | timestamptz | |

## health_checkins
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| profile_id | uuid → crew_profiles | cascade delete |
| recorded_at | timestamptz | |
| sleep_duration_hours | numeric(4,2) | 0–24 |
| mood_rating | smallint | 1–5 |
| resting_heart_rate | smallint | bpm, 20–250 |
| source | text | `self_report` \| `wearable` \| `synthetic` |
| is_simulated | boolean (default true) | |
| data_quality | jsonb | completeness / flags |

Index: `(profile_id, recorded_at desc)`.

## environment_readings
Mission-context telemetry — **not** personal data or personal dose.

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| recorded_at | timestamptz | Used to align with check-ins by time |
| source | text | e.g. `synthetic`, `nasa_pims`, `nasa_radlab` |
| instrument | text | |
| measurement_type | text | `acceleration_quasi_steady` \| `acceleration_vibratory` \| `absorbed_dose_rate` \| `dose_equivalent_rate` \| `particle_flux` \| `ppco2` \| `proton_flux_ge10mev` |
| value | double precision | |
| unit | text | `micro-g`, `uGy/h`, `uSv/h`, `mmHg`, `pfu` |
| location_context | text | Module/vehicle, never a person |
| is_simulated / is_stale | boolean | |
| source_retrieved_at | timestamptz | Freshness |
| metadata | jsonb | |

Index: `(measurement_type, recorded_at desc)`.

## mission_events
Space weather (DONKI, NOAA S-scale) and environment excursions. Context only, never personal data.

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| event_type | text | `SEP` \| `FLR` \| `CME` \| `GST` \| `S_SCALE` \| `CO2_EXCURSION` |
| level | text, nullable | e.g. `S2`, `X1.2`, `ppco2_above_1h_limit` |
| start_time / end_time | timestamptz | `end_time >= start_time` when set |
| source | text | `donki` \| `noaa_swpc` \| `synthetic` |
| source_event_id | text, nullable | DONKI `activityID`; unique per source when set |
| link | text, nullable | |
| is_simulated | boolean (default true) | |
| metadata | jsonb | |
| created_at | timestamptz | |

Index: `(start_time desc)`.

## anomaly_results
Reserved for future analysis output. Nothing populates it yet.

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| profile_id | uuid → crew_profiles | |
| checkin_id | uuid → health_checkins, nullable | |
| score | double precision | |
| review_label | text | `within_baseline` \| `worth_reviewing` \| `insufficient_data` |
| explanation | jsonb | Plain-language text + contributing features |
| model_version | text | |
| created_at | timestamptz | |

## Access (RLS)
| Table | Browser (`authenticated`) | Server (secret key) |
|---|---|---|
| crew_profiles | read/update own | full |
| health_checkins | read/insert own | full |
| environment_readings | read all | write (future ingestion) |
| mission_events | read all | write |
| anomaly_results | read own | write (future analysis) |

`anon` has no access. If the demo runs without accounts, add narrowly-scoped `anon` SELECT policies restricted to `is_fictional = true` profiles (placeholder noted in the migration).
