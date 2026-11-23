# Status

Living handoff doc for people and agents. Rules (also in [AGENTS.md](../AGENTS.md)):

- Claim a task by moving it from **Next up** to **Active** with your name/agent and branch.
- When you finish, move it to **Done**, tick any milestone it completes, and add a **Changelog** line, all in the same commit as the work.
- If you get stuck, move it to **Blocked** and say what you need.
- Keep entries to one or two lines. Link files instead of describing them.

**Snapshot**: Supabase project live with both migrations applied and the synthetic dataset loaded. No screens, no ML scoring, no NASA integrations, no deployment.
**Demo deadline**: _set this_

## Milestones

| # | Milestone | Done when | State |
|---|---|---|---|
| M0 | Scaffold | Web builds, `GET /health` 200, `POST /analyze` 501, migration written | Done |
| M1 | Supabase live | Project created, `.env` filled, migration applied, demo access policy decided | Done |
| M2 | Synthetic data | Deterministic generator for profiles, check-ins and mission readings, all labeled simulated, loadable into Supabase | Done |
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

1. [M3] Apply `supabase/migrations/20261123000000_protect_form_checkins.sql` in the Supabase SQL Editor (before the form writes check-ins).
2. [M3] Create demo accounts in Supabase Auth (one per crew profile) and set `crew_profiles.user_id` for each, so signed-in users see their own profile under the existing RLS. Links survive reloads of `load_synthetic.psql`.
3. [API] Add a first test for `GET /health` and the current `POST /analyze` 501 (pytest is now installed).
4. [M4] Feature prep + personal baseline (rolling median, short-term trend) in `apps/api/app/ml/`.
5. [M4] Isolation Forest scoring + per-indicator explanation; implement `POST /analyze` per `docs/api-contract.md`.
6. [M4] Environment status labels (`ppco2_above_1h_limit`, `ppco2_above_7d_guidance`, `solar_storm_S1`..`S5`) per `synthetic-data.md` section 8. Kept separate from `/analyze`.
7. [M3] Web: `src/api/` client, profile picker, Daily Check-in form.
8. [M5] Web: Mission Overview, Health Trends (Recharts), mission-context panel, Flag Details panel.
9. [M6] Demo script + walkthrough check.
10. [M7] Save DONKI SEP and NOAA proton samples (commands in `data-sources.md`), then `providers/noaa_swpc.py` and `providers/donki.py`; add `NASA_API_KEY` to `.env.example`.

## Done

- [M1] Supabase project created, `.env` filled, both migrations applied. Demo access decided: **sign-in** (existing owner-only RLS stays; no `anon` policies).
- [M2] Synthetic dataset loaded into Supabase with `supabase/load_synthetic.psql`; row counts match `synthetic_manifest.json`.
- [M2] Migration `20261116000000_environment_types_and_mission_events.sql` (new measurement types, `mission_events` + RLS) and loader `supabase/load_synthetic.psql`; tested on local Postgres 16 (all 86,219 rows load, re-run safe).
- [M2] Synthetic generator `synth-0.2.0` in [apps/api/app/synthetic/](../apps/api/app/synthetic/) with 21 pytest checks (determinism, V1 4033 guardrail, CO2 1 h/7 d, scenarios). Branch `ml/synthetic-generator`.
- [M0] Scaffold: React/Vite web, FastAPI with `/health` and 501 `/analyze`, schema + RLS migration, docs, pinned deps and lockfiles.
- Agent workflow docs: `AGENTS.md` and this file.

## Open issues and decisions

| Item | Type | Notes |
|---|---|---|
| Demo auth | Decided | Demo uses sign-in: one Supabase Auth account per fictional crew profile, linked through `crew_profiles.user_id`. Existing owner-only RLS stays; no `anon` policies. |
| Minimum history for a baseline | Decided | Median of the last 14 check-ins (count-based, not calendar days), 7 earlier check-ins minimum. Documented in `api-contract.md`. |
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

- 2026-11-23: Migration 3 (form check-ins can't be `synthetic`, `is_simulated` defaults to false); loader now replaces only synthetic rows and keeps profiles, account links and form check-ins; baseline defined as last 14 check-ins (db, docs).

- 2026-11-21: Supabase project live, both migrations applied, synthetic data loaded; demo uses sign-in. M1 and M2 done (db).
- 2026-11-16: Migration 2 (measurement types, `mission_events`) and `supabase/load_synthetic.psql` loader; `data-model.md` updated (db).
- 2026-11-16: Synthetic data generator `synth-0.2.0` (CREW-A to D, S0 to S7, 5 telemetry series at 5 min, 2 events), shared `app/limits.py`, pytest + 21 generator tests, `npm run synth` / `npm run test:api` (ml).
- 2026-11-16: Aligned data plan with NASA-STD-3001, OCHMO-TB-020/004/030 and NOAA S-scale: official limits table, ppCO2 and proton flux streams, scenarios S5 to S7, environment status labels, demo vs live source split (docs).
- 2026-11-15: Added `docs/synthetic-data.md`: source roles, schema change, check-in and telemetry generator spec (docs, ml).
- 2026-11-14: Added `AGENTS.md` and `docs/STATUS.md` for the agent workflow (docs).
- 2026-11-14: Initial scaffold: React/Vite web, FastAPI, Supabase schema + RLS, docs (all).
