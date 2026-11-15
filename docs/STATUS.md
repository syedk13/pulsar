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
| M7 | Optional NASA adapters | At least one source (PIMS or RadLab) behind `app/providers/`, cached, provenance shown | Optional |
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
3. [M2] Synthetic data generator in `apps/api/app/synthetic/`: fixed seed, 3 to 4 fictional profiles, about 30 to 60 days each, scenarios for gradual sleep decline and an unusual resting heart rate trend, plus timestamp-aligned acceleration and radiation readings.
4. [M2] Seed script that loads synthetic data into Supabase (server key) or exports SQL/CSV.
5. [API] Add pytest and a first test for `GET /health` and the current `POST /analyze` 501.
6. [M4] Feature prep + personal baseline (rolling median, short-term trend) in `apps/api/app/ml/`.
7. [M4] Isolation Forest scoring + per-indicator explanation; implement `POST /analyze` per `docs/api-contract.md`.
8. [M3] Web: `src/api/` client, profile picker, Daily Check-in form.
9. [M5] Web: Mission Overview, Health Trends (Recharts), mission-context panel, Flag Details panel.
10. [M6] Demo script + walkthrough check.

## Done

- [M0] Scaffold: React/Vite web, FastAPI with `/health` and 501 `/analyze`, schema + RLS migration, docs, pinned deps and lockfiles.
- Agent workflow docs: `AGENTS.md` and this file.

## Open issues and decisions

| Item | Type | Notes |
|---|---|---|
| Demo auth | Decision | Signed-in fictional astronauts vs anon read-only policies. Blocks M1 item 2. |
| Minimum history for a baseline | Decision | How many check-ins before scoring instead of `insufficient_data`. Document in `api-contract.md`. |
| `/analyze` trigger | Decision | Called by the web after each check-in, or batch over all profiles? |
| Supabase client crashes without env | Issue | `apps/web/src/lib/supabase.ts` calls `createClient` at import; guard before first use. |
| `/analyze` returns 422 on bad body | Note | Body is validated before the 501. Fine for now; keep in mind for tests. |
| Offline-tolerant check-ins | Later | Desirable for long missions; not in the MVP. |

## Changelog

Newest first. Format: `YYYY-MM-DD: what changed (area)`.

- 2026-11-14: Added `AGENTS.md` and `docs/STATUS.md` for the agent workflow (docs).
- 2026-11-14: Initial scaffold: React/Vite web, FastAPI, Supabase schema + RLS, docs (all).
