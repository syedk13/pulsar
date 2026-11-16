# Data sources

> Status: no source is connected yet. Generator spec and limits: [synthetic-data.md](synthetic-data.md).

## Which metrics come from where

| Metric | Demo mode (default, `DEMO_MODE=true`) | Live mode (optional) | Official reference |
|---|---|---|---|
| Sleep, resting heart rate, mood (`health_checkins`) | Local generator | Crew check-in form (still fictional profiles) | None; personal baseline only |
| Module absorbed dose rate, dose equivalent rate | Local generator | Local generator (RadLab adapter possible later) | V1 4033 used only as a generator guardrail |
| Quasi-steady acceleration | Local generator | Local generator | None |
| Cabin ppCO2 | Local generator | Local generator | V2 6004 (1-hour ≤ 3 mmHg), TB-004 7-day guidance (< 2.5 mmHg) |
| ≥10 MeV proton flux + S-level | Local generator | **NOAA SWPC hook** (GOES 5-minute integral protons) | NOAA S-scale |
| Space weather events (SEP, FLR, CME, GST) | Saved DONKI sample + simulated `S5` event | **DONKI hook** | None (context only) |
| Bone mineral density | Not modeled | Not modeled | Pre/post-mission DXA only; no in-flight measurement exists |

## Direct hooks (live mode only)

Both live in `apps/api/app/providers/`, one module each, write only to `environment_readings` or `mission_events`, and never touch crew tables. If a hook fails, the UI shows the last saved reading with `is_stale = true`; the demo never depends on it.

### NOAA SWPC GOES proton flux (`providers/noaa_swpc.py`)
- URL: `https://services.swpc.noaa.gov/json/goes/primary/integral-protons-1-day.json` (also `6-hour`, `3-day`, `7-day`). No key.
- Use the `>=10 MeV` channel. Store as `measurement_type = 'proton_flux_ge10mev'`, unit `pfu`, `location_context = 'Geostationary orbit (GOES primary)'`, `source = 'noaa_swpc'`, `is_simulated = false`.
- Derive the S-level with the thresholds in `synthetic-data.md` section 2 and write an `S_SCALE` row to `mission_events` when flux crosses 10 pfu.
- Saved sample for tests and offline demo: `apps/api/app/providers/samples/noaa_integral_protons_1day_<date>.json`.

### DONKI (`providers/donki.py`)
- URL: `https://api.nasa.gov/DONKI/{SEP,FLR,CME,GST}?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&api_key=...` (server env var `NASA_API_KEY`, `DEMO_KEY` for light testing), or the CCMC mirror `https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get/SEP?startDate=...&endDate=...` without a key.
- Store each event in `mission_events` with `source_event_id = activityID` (e.g. `sepID`), times, `link`, and linked events in `metadata`.
- Saved sample: `apps/api/app/providers/samples/donki_sep_<range>.json`. Suggested range with plenty of linked activity: `2024-05-08` to `2024-05-20`.

To save the samples (run from the repo root on a machine with internet):
```bash
mkdir -p apps/api/app/providers/samples
curl -s "https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get/SEP?startDate=2024-05-08&endDate=2024-05-20" \
  -o apps/api/app/providers/samples/donki_sep_2024-05-08_2024-05-20.json
curl -s "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-1-day.json" \
  -o "apps/api/app/providers/samples/noaa_integral_protons_1day_$(date -u +%F).json"
```

## Reference documents (no hook)

| Document | Used for |
|---|---|
| NASA-STD-3001 Vol 1 Rev C, Vol 2 Rev D | Official limits in `synthetic-data.md` section 2 |
| OCHMO-TB-020 Design for Ionizing Radiation Protection (Rev G) | Radiation limits and monitoring requirements |
| OCHMO-TB-004 Carbon Dioxide | ppCO2 limit and 7-day guidance |
| Bone loss brief (TB-030, now OCHMO-MTB-013 Rev D) | Reason bone density is not modeled |
| OSDR RadLab, NASA PIMS | Shape of simulated radiation and acceleration |
| LSDA, OSDR human data, Curiosity RAD, NTRS | Out of MVP scope (gated, wrong environment, or documents only) |

## Rules
- Every stored reading carries source, instrument, unit, timestamp, `source_retrieved_at`, and `is_simulated` / `is_stale`, and the UI shows them.
- Module, station, satellite or rover readings are **environment context only**, never an individual's dose.
- Environment limit labels stay on the mission-context panel; they are never inputs to, or explanations for, a crew health flag.
- No generated value may be labeled as NASA or NOAA data.
- API keys are server-side env vars only (`NASA_API_KEY`).
