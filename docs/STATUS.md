# Status

Living handoff doc for people and agents. Rules (also in [AGENTS.md](../AGENTS.md)):

- Claim a task by moving it from **Next up** to **Active** with your name/agent and branch.
- When you finish, move it to **Done**, tick any milestone it completes, and add a **Changelog** line, all in the same commit as the work.
- If you get stuck, move it to **Blocked** and say what you need.
- Keep entries to one or two lines. Link files instead of describing them.

**Snapshot**: scaffold only. No screens, no ML, no seeded data, no NASA integrations, no remote Supabase project, no deployment.
**Demo deadline**: _set this_

## Milestones

| # | Milestone | Done when | State |
|---|---|---|---|
| M0 | Scaffold | Web builds, `GET /health` 200, `POST /analyze` 501, migration written | Done |
| M1 | Supabase live | Project created, `.env` filled, migration applied, demo access policy decided | Not started |
| M2 | Synthetic data | Deterministic generator for profiles, check-ins and mission readings, all labeled simulated, loadable into Supabase | Not started |
| M3 | Check-in flow | Web form saves a check-in for a fictional profile and shows it back | Not started |
| M4 | Baselines + `/analyze` | Per-profile baseline, anomaly score, explanation, `insufficient_data` path, result saved to `anomaly_results` | Not started |
| M5 | Core screens | Mission Overview, Health Trends with baseline band, separate mission-context panel, Flag Details | Not started |
| M6 | Demo ready | Scripted walkthrough runs end to end on synthetic data with no external keys | Not started |
| M7 | Optional live hooks | NOAA SWPC proton flux (S-level) and DONKI events behind `app/providers/`, saved samples for offline, provenance shown | Optional |
| M8 | Deploy | Web on Vercel, API on Render, CORS set | Not started |

## Active

| Task | Area | Owner | Branch | Started | Notes |
|---|---|---|---|---|---|
| _none_ | | | | | |

## Blocked

| Task | Waiting on | Since |
|---|---|---|
| _none_ | | |

## Next up

Ordered. Milestone in brackets. Take from the top unless you are told otherwise.

1. [M1] Create the Supabase project, fill `.env`, apply `supabase/migrations/20261114000000_initial_schema.sql`. (Manual, project owner.)
2. [M1] Decide sign-in vs no sign-in for the demo. If no sign-in, add a new migration with `anon` SELECT policies limited to `is_fictional = true`.
3. [M2] New migration: widen `environment_readings.measurement_type` (adds `ppco2`, `proton_flux_ge10mev`) and add `mission_events` (see `docs/synthetic-data.md` section 3). Update `data-model.md`.
4. [M2] Synthetic data generator in `apps/api/app/synthetic/` per `docs/synthetic-data.md` (`synth-0.2.0`): seed 2026, CREW-A to D, 60 days, scenarios S0 to S7; radiation, acceleration, ppCO2 and proton flux every 5 minutes; tests for the V1 4033 guardrail and CO2 checks.
5. [M2] Seed script that loads synthetic data into Supabase (server key) or exports SQL/CSV.
6. [API] Add pytest and a first test for `GET /health` and the current `POST /analyze` 501.
7. [M4] Feature prep + personal baseline (rolling median, short-term trend) in `apps/api/app/ml/`.
8. [M4] Isolation Forest scoring + per-indicator explanation; implement `POST /analyze` per `docs/api-contract.md`.
9. [M4] Environment status labels (`ppco2_above_1h_limit`, `ppco2_above_7d_guidance`, `solar_storm_S1`..`S5`) per `synthetic-data.md` section 8. Kept separate from `/analyze`.
10. [M3] Web: `src/api/` client, profile picker, Daily Check-in form.
11. [M5] Web: Mission Overview, Health Trends (Recharts), mission-context panel, Flag Details panel.
12. [M6] Demo script + walkthrough check.
13. [M7] Save DONKI SEP and NOAA proton samples (commands in `data-sources.md`), then `providers/noaa_swpc.py` and `providers/donki.py`; add `NASA_API_KEY` to `.env.example`.

## Done

- [M0] Scaffold: React/Vite web, FastAPI with `/health` and 501 `/analyze`, schema + RLS migration, docs, pinned deps and lockfiles.
- Agent workflow docs: `AGENTS.md` and this file.

## Open issues and decisions

| Item | Type | Notes |
|---|---|---|
| Demo auth | Decision | Signed-in fictional astronauts vs anon read-only policies. Blocks M1 item 2. |
| Minimum history for a baseline | Decision | Proposed in `synthetic-data.md`: 14-day rolling median, 7 check-ins minimum. Confirm and document in `api-contract.md`. |
| Live NASA data | Decided | No public raw daily crew health data exists; health is fully synthetic. Environment is synthetic. Live mode adds only NOAA proton flux and DONKI events. See `data-sources.md`. |
| Official limits | Decided | Only environment limits are used: ppCO2 1-hour ≤ 3 mmHg (V2 6004), 7-day < 2.5 mmHg (TB-004 guidance), NOAA S-scale. Radiation PELs (600 mSv career, 250 mSv SPE) need personal effective dose, so they are not compared to module readings; V1 4033 (1.3 mSv/day) is a generator guardrail only. Crew health flags stay personal-baseline. |
| Bone density | Decided | Not modeled: no in-flight measurement exists; limits are pre/post-mission DXA. |
| Brief numbering | Note | NASA's TB-030 bone file now reads OCHMO-MTB-013 Rev D (Feb 2026); TB-020 is "Design for Ionizing Radiation Protection", Rev G. Recheck revisions before citing in the pitch. |
| `/analyze` trigger | Decision | Called by the web after each check-in, or batch over all profiles? |
| Supabase client crashes without env | Issue | `apps/web/src/lib/supabase.ts` calls `createClient` at import; guard before first use. |
| `/analyze` returns 422 on bad body | Note | Body is validated before the 501. Fine for now; keep in mind for tests. |
| Offline-tolerant check-ins | Later | Desirable for long missions; not in the MVP. |

## Changelog

Newest first. Format: `YYYY-MM-DD: what changed (area)`.

- 2026-11-16: Aligned data plan with NASA-STD-3001, OCHMO-TB-020/004/030 and NOAA S-scale: official limits table, ppCO2 and proton flux streams, scenarios S5 to S7, environment status labels, demo vs live source split (docs).
- 2026-11-15: Added `docs/synthetic-data.md`: source roles, schema change, check-in and telemetry generator spec (docs, ml).
- 2026-11-14: Added `AGENTS.md` and `docs/STATUS.md` for the agent workflow (docs).
- 2026-11-14: Initial scaffold: React/Vite web, FastAPI, Supabase schema + RLS, docs (all).
