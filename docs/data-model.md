# Data model

> Status: schema defined in `supabase/migrations/20261114000000_initial_schema.sql`. Not applied to any project; no seed data.

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
| measurement_type | text | `acceleration` \| `radiation` |
| value | double precision | |
| unit | text | e.g. `micro-g`, `uGy/h` |
| location_context | text | Module/vehicle, never a person |
| is_simulated / is_stale | boolean | |
| source_retrieved_at | timestamptz | Freshness |
| metadata | jsonb | |

Index: `(measurement_type, recorded_at desc)`.

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
| anomaly_results | read own | write (future analysis) |

`anon` has no access. If the demo runs without accounts, add narrowly-scoped `anon` SELECT policies restricted to `is_fictional = true` profiles (placeholder noted in the migration).
