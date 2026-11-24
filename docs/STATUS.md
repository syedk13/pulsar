# Status

Living handoff doc for people and agents. Rules (also in [AGENTS.md](../AGENTS.md)):

- Claim a task by moving it from **Next up** to **Active** with your name/agent and branch.
- When you finish, move it to **Done**, tick any milestone it completes, and add a **Changelog** line, all in the same commit as the work.
- If you get stuck, move it to **Blocked** and say what you need.
- Keep entries to one or two lines. Link files instead of describing them.

**Snapshot**: Supabase project live with all four migrations applied and synthetic data loaded, and the web app has sign-in plus the Daily Check-in screen, and `POST /analyze` compares check-ins with personal baselines, but no trend screens, NASA integrations or deployment yet.
**Demo deadline**: _set this_

## Milestones

| # | Milestone | Done when | State |
|---|---|---|---|
| M0 | Scaffold | Web builds, `GET /health` 200, `POST /analyze` 501, migration written | Done |
| M1 | Supabase live | Project created, `.env` filled, migration applied, demo access policy decided | Done |
| M2 | Synthetic data | Deterministic generator for profiles, check-ins and mission readings, all labeled simulated, loadable into Supabase | Done |
| M3 | Check-in flow | Web form saves a check-in for a fictional profile and shows it back | Done |
| M4 | Baselines + `/analyze` | Per-profile baseline, anomaly score, explanation, `insufficient_data` path, result saved to `anomaly_results` | In progress (API done and tested with fakes; live test against Supabase pending) |
| M5 | Core screens | Mission Overview, Health Trends with baseline band, separate mission-context panel with environment status labels, Flag Details | Not started |
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

1. [M4] Live test of `POST /analyze` against Supabase with a demo account's access token: 401 without a token, 404 for another profile, a result for the latest check-in, one row per check-in in `anomaly_results`. Then mark M4 done.
2. [M5] Web: Mission Overview, Health Trends (Recharts), mission-context panel, Flag Details panel.
3. [M5] Environment status labels (`ppco2_above_1h_limit`, `ppco2_above_7d_guidance`, `solar_storm_S1`..`S5`) per `synthetic-data.md` section 8. Kept separate from `/analyze`, shown on the mission-context panel.
4. [M6] Demo script + walkthrough check.
5. [M7] Save DONKI SEP and NOAA proton samples (commands in `data-sources.md`), then `providers/noaa_swpc.py` and `providers/donki.py`; add `NASA_API_KEY` to `.env.example`.

## Done

- [M4] Personal baselines + `POST /analyze` (`baseline-iforest-0.1.0`) in [apps/api/app/ml/](../apps/api/app/ml/): last-14 median, MAD spread, trend, pooled Isolation Forest, plain-language explanation, `insufficient_data` path, Supabase-token auth, results saved to `anomaly_results`. 56 pytest checks incl. scenario acceptance. Branch `ml/analyze-baseline`.
- [M3] Check-in flow verified live against Supabase: sign-in, linked profile, validation, one-per-day cap, reload keeps form check-ins.
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
| Supabase client crashes without env | Fixed | `supabase` is `null` when env is missing; the app shows a configuration message. |
| Check-ins per day | Decided | One per crew profile per UTC day. Enforced by the database (migration 4: unique index, server-side time) and the app (form disabled, error 23505 handled). |
| Profile picker | Dropped | Demo uses sign-in, so the profile comes from `crew_profiles.user_id`; no picker. |
| `/analyze` status order | Note | 401 (token) is checked before the body; a bad body with a valid token is 422. |
| Gradual changes vs rolling baseline | Known limit | The last-14 median follows a slow drift, so CREW-B's sleep decline is first flagged on day 46, not about day 42, and mood is not named. See `api-contract.md` scenario table. Revisit in a later model version (e.g. a fixed reference period) if the demo needs it. |
| Offline-tolerant check-ins | Later | Desirable for long missions; not in the MVP. |

## Changelog

Newest first. Format: `YYYY-MM-DD: what changed (area)`.

- 2026-11-24: M4 API: personal baselines, Isolation Forest score, explanations and `insufficient_data` in `app/ml/`; `POST /analyze` with Supabase-token auth saves to `anomaly_results`; `/health` test; environment status labels moved to M5 (ml, api, docs).
- 2026-11-23: M3 done; check-ins capped at one per profile per UTC day (web, db).
- 2026-11-23: Web check-in flow: email sign-in, own crew profile lookup, validated Daily Check-in form (writes `self_report`, `is_simulated = false`), recent history with provenance badges; guarded Supabase client (web).
- 2026-11-23: Migration 3 (form check-ins can't be `synthetic`, `is_simulated` defaults to false); loader now replaces only synthetic rows and keeps profiles, account links and form check-ins; baseline defined as last 14 check-ins (db, docs).

- 2026-11-21: Supabase project live, both migrations applied, synthetic data loaded; demo uses sign-in. M1 and M2 done (db).
- 2026-11-16: Migration 2 (measurement types, `mission_events`) and `supabase/load_synthetic.psql` loader; `data-model.md` updated (db).
- 2026-11-16: Synthetic data generator `synth-0.2.0` (CREW-A to D, S0 to S7, 5 telemetry series at 5 min, 2 events), shared `app/limits.py`, pytest + 21 generator tests, `npm run synth` / `npm run test:api` (ml).
- 2026-11-16: Aligned data plan with NASA-STD-3001, OCHMO-TB-020/004/030 and NOAA S-scale: official limits table, ppCO2 and proton flux streams, scenarios S5 to S7, environment status labels, demo vs live source split (docs).
- 2026-11-15: Added `docs/synthetic-data.md`: source roles, schema change, check-in and telemetry generator spec (docs, ml).
- 2026-11-14: Added `AGENTS.md` and `docs/STATUS.md` for the agent workflow (docs).
- 2026-11-14: Initial scaffold: React/Vite web, FastAPI, Supabase schema + RLS, docs (all).
