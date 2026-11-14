# Data sources

> Status: all sources below are **future work**. Nothing is connected, ingested, or keyed.

| Source | Planned use | Status |
|---|---|---|
| **Synthetic crew readings** | Primary demo data for check-ins; clearly labelled `source = synthetic`, `is_simulated = true` | Planned |
| **NASA Glenn PIMS** (Principal Investigator Microgravity Services) | ISS acceleration / microgravity context → `environment_readings` (`acceleration`) | Possible |
| **NASA RadLab** | Public radiation instrument telemetry → `environment_readings` (`radiation`) | Possible |
| NASA OSDR (Open Science Data Repository) | Research context | Optional |
| NASA DONKI (space weather) | Solar event context | Optional |
| Curiosity RAD | Archived Mars-surface radiation context | Optional |
| LSDA (Life Sciences Data Archive) | Research context | Optional |
| NTRS (Technical Reports Server) | Literature references | Optional |

## Rules for future integrations
- Each provider is an isolated adapter in `apps/api` (see `architecture.md`); it never touches check-in tables.
- Every stored reading carries source, instrument, unit, timestamp, `source_retrieved_at`, and `is_simulated` / `is_stale` flags, and the UI must display them.
- Vehicle, station, or rover radiation readings are **environmental context only** and must never be presented as an individual astronaut's personal dose.
- No fabricated readings may be labelled as NASA data.
- Any API keys are server-side env vars only.
