# Synthetic data spec

> Status: implemented in `apps/api/app/synthetic/` (`npm run synth`). Implementation choices the spec left open are listed in section 11.

Everything here is **simulated demo data**. Environment limits come from NASA-STD-3001, the OCHMO technical briefs and the NOAA space weather scales (section 2). Crew check-in ranges come from published spaceflight studies, because none of those standards set in-mission ranges or alert values for sleep, resting heart rate or mood. Never label a generated value as NASA or NOAA data.

## 1. Source roles (decided)

| Source | Direct hook? | Role in Pulsar | Do not |
|---|---|---|---|
| NASA-STD-3001 Vol 1 Rev C and Vol 2 Rev D | No (documents) | Official limits for **environment** context lines and generator guardrails (section 2) | Use them as crew health or diagnostic thresholds |
| OCHMO-TB-020 Design for Ionizing Radiation Protection (Rev G, Jun 2025) | No (document) | Radiation limits and monitoring requirements (section 2) | Compare an instrument reading to a personal-dose limit |
| OCHMO-TB-004 Carbon Dioxide | No (document) | Cabin ppCO2 limit and 7-day headache-risk guidance (section 2) | Use CO2 to explain a crew member's health flag |
| Bone loss brief (published as OCHMO-TB-030; NASA's file at that URL now reads OCHMO-MTB-013 Rev D, Feb 2026) | No (document) | Explains why bone density is **not** modeled (section 9) | Simulate in-flight bone density |
| DONKI | **Yes, optional** (`SEP`, `FLR`, `CME`, `GST`) | Space weather event context in live mode; a saved sample replays in demo mode | Turn an event into a dose value |
| NOAA SWPC GOES integral protons + S-scale | **Yes, optional** (5-minute ≥10 MeV flux) | Solar radiation storm level (S1 to S5) as context in live mode; simulated in demo mode | Treat flux at geostationary orbit as ISS or crew dose |
| OSDR RadLab | Technically yes | Shapes the synthetic module radiation stream | Treat module dose rate as personal dose |
| NASA PIMS (MAMS, SAMS-II) | Not practical (raw sensor archives) | Shapes the synthetic acceleration stream | Imply acceleration measures a body's response |
| LSDA, OSDR human data (Inspiration4) | No (gated, needs approval) | Out of scope | Assume a public daily crew series exists |
| Curiosity RAD | Wrong environment | Optional Mars scenario only | Use as ISS or astronaut dose |
| NTRS | Documents | Evidence library | Expect telemetry |

**Core rule:** demo mode uses only the local generator and saved samples, with no keys and no network. Live mode adds DONKI and NOAA as optional context. Crew health data is always synthetic.

## 2. Official reference limits

These are the only official numbers Pulsar uses. Each row says what it actually applies to, so we never compare the wrong quantity.

### Radiation (NASA-STD-3001 Vol 1 Rev C, via OCHMO-TB-020 Rev G)

| Req. | Limit | Applies to | Pulsar use |
|---|---|---|---|
| V1 4029 | ALARA, no number | All crew exposure | Copy only |
| V1 4030 | Career effective dose < **600 mSv** | A person's career effective dose | **Not used.** Our data is a module instrument reading, not personal effective dose |
| V1 4031 | Design reference SPE < **250 mSv** effective dose | Vehicle shielding design | **Not used** for the same reason |
| V1 4032 | Nuclear sources < **20 mSv per mission year** | Onboard nuclear technology | Not applicable |
| V1 4033 | GCR design dose rate < **1.3 mSv/day** free space, < **0.9 mSv/day** planetary surface (habitats used > 60 days) | Vehicle design | Generator sanity ceiling only (section 7a), never a live flag |
| V2 6164 | Alert when exposure rates exceed "predefined thresholds" | Monitoring system | No values are published, so Pulsar shows **no official radiation alert** |

The current brief gives no organ-specific 30-day or 1-year limits, so we do not use older tables that do.

### Carbon dioxide (OCHMO-TB-004; requirement is in **Vol 2**, not Vol 1)

| Source | Limit | Averaging | Pulsar use |
|---|---|---|---|
| V2 6004 | ppCO2 **≤ 3 mmHg** in the habitable volume | 1-hour mean | Environment flag `ppco2_above_1h_limit` |
| TB-004 guidance (not a requirement) | **< 2.5 mmHg** keeps headache risk below 1% | 7-day mean | Environment flag `ppco2_above_7d_guidance` |
| TB-004 historical | ISS range **1 to 9 mmHg** | n/a | Generator bound |

TB-004 also lists anecdotal symptoms by CO2 level. Pulsar does **not** show them next to crew data.

### Solar radiation storms (NOAA S-scale, ≥10 MeV integral proton flux at geostationary orbit)

| Level | Flux (pfu) | Label |
|---|---|---|
| S1 | ≥ 10 | Minor |
| S2 | ≥ 100 | Moderate |
| S3 | ≥ 1,000 | Strong |
| S4 | ≥ 10,000 | Severe |
| S5 | ≥ 100,000 | Extreme |

1 pfu = 1 particle per cm²·s·sr. A storm starts when the flux first reaches 10 pfu and ends at the last reading at or above 10 pfu. NASA's radiation brief does not map S-levels to crew dose, so Pulsar shows the S-level as space weather context only.

## 3. Schema changes needed

Keep existing column names (`recorded_at`, `mood_rating`, `resting_heart_rate`).

1. **Required: widen `environment_readings.measurement_type`** (new migration):

   ```sql
   alter table public.environment_readings
     drop constraint environment_readings_measurement_type_check;
   alter table public.environment_readings
     add constraint environment_readings_measurement_type_check
     check (measurement_type in (
       'acceleration_quasi_steady', 'acceleration_vibratory',
       'absorbed_dose_rate', 'dose_equivalent_rate', 'particle_flux',
       'ppco2', 'proton_flux_ge10mev'));
   ```
   Update `docs/data-model.md` in the same commit.

2. **Recommended now: `mission_events` table** for DONKI events, NOAA S-level storms and simulated equivalents: `id`, `event_type` (`SEP`, `FLR`, `CME`, `GST`, `S_SCALE`, `CO2_EXCURSION`), `level` (e.g. `S2`, `X1.2`), `start_time`, `end_time`, `source` (`donki`, `noaa_swpc`, `synthetic`), `source_event_id` (DONKI `activityID`), `link`, `is_simulated`, `metadata` jsonb. Read-only for signed-in users, server writes only.

3. **No change to `health_checkins`.** Generator metadata goes in `data_quality`.

## 4. Mission frame

| Setting | Value |
|---|---|
| Seed | `2026` (one `numpy.random.default_rng(seed)`; per-stream children via `rng.spawn`) |
| Mission length | 60 days |
| Mission start | `2026-09-01T00:00:00Z` (all timestamps UTC) |
| Mission label | `Pulsar Demo Mission (simulated)` |
| Generator version | `synth-0.2.0`, in every row's metadata |

## 5. Daily crew check-ins (`health_checkins`)

None of the listed standards define in-mission values or alert thresholds for these fields, so ranges come from published studies, and flags stay **relative to each person's own baseline** (section 8).

One row per profile per day, `recorded_at` = day start + 07:00 UTC ± uniform 30 min.

| Field | Unit | Per-profile baseline | Day-to-day noise | Clip | Rounding |
|---|---|---|---|---|---|
| `sleep_duration_hours` | hours | uniform 5.6 to 7.0 | normal, SD 0.6 | 3.0 to 9.5 | 0.1 h |
| `resting_heart_rate` | bpm, morning resting | uniform 52 to 66 | normal, SD 2.5 | 40 to 110 | integer |
| `mood_rating` | scale below | latent uniform 3.4 to 4.2 | normal, SD 0.5 | 1 to 5 | integer |

Couplings (demo assumptions): RHR +1 bpm per hour of sleep below baseline; latent mood ±0.3 per hour of sleep above or below baseline.

Basis: ISS astronauts averaged about 6.1 h of sleep in flight (8.5 h scheduled) and about 1 h less when circadian timing was misaligned; long-duration ISS studies found heart rate roughly unchanged from preflight. Mood has no NASA calibration.

**Mood scale** `pulsar-mood-1to5-v1`: 1 Very low, 2 Low, 3 Okay, 4 Good, 5 Very good.

**Fixed:** `source = 'synthetic'`, `is_simulated = true`.

**`data_quality`:**
```json
{"generator_version": "synth-0.2.0", "scenario_id": "S1_sleep_decline",
 "hr_kind": "resting_morning", "mood_scale": "pulsar-mood-1to5-v1", "missing_fields": []}
```

**Missing data:** 6% of days per profile have no row (never inside a scenario's key window); 2% of rows have one `null` field, listed in `missing_fields`.

## 6. Profiles and scenarios

Health scenarios and environment scenarios are placed on **different days** on purpose, so the demo never suggests the environment caused a health change.

| Id | Who | Days | What happens | Expected result |
|---|---|---|---|---|
| `S0_stable` | CREW-A | all | Baseline only | `within_baseline` |
| `S1_sleep_decline` | CREW-B | 36 to 50 | Sleep drops linearly by 1.5 h, mood follows; recovers 51 to 55 | `worth_reviewing` from about day 42 (sleep, mood) |
| `S2_rhr_trend` | CREW-C | 42 to 49 | RHR +1.5 bpm/day to +10, sleep unchanged | `worth_reviewing` (RHR only) |
| `S3_new_profile` | CREW-D | 56 to 60 | Only 5 days of data | `insufficient_data` |
| `S4_schedule_shift` | all | 20 to 21 | Sleep −1.0 h for everyone | Short dip |
| `S5_solar_storm` | environment | 27 to 28 | Simulated S2 storm (section 7d) and matching `mission_events` row | Space weather banner "S2 Moderate (simulated)" |
| `S6_co2_excursion` | environment | 12 | Simulated CO2 scrubber slowdown (section 7c) | `ppco2_above_1h_limit` for a few hours |
| `S7_stale_feed` | environment | 33 | 6-hour gap, readings marked stale | Freshness label demo |

Profiles: `CREW-A` to `CREW-D`, `display_name` like `Crew A (fictional)`, `is_fictional = true`. True generator parameters go in `synthetic_manifest.json`, **not** in `baseline_metadata`.

## 7. Environment telemetry (`environment_readings`)

Separate stream, same mission clock, every **5 minutes** (matches the GOES 5-minute averages). Charts show hourly mean and max.

### 7a. Module radiation

**`absorbed_dose_rate` (uGy/h)** = background + South Atlantic Anomaly (SAA) passes + noise.

| Component | Spec |
|---|---|
| Background | 2 to 6 uGy/h, sinusoid with the 92-minute orbit |
| SAA | One daily block of 5 to 6 consecutive orbits, each pass about 15 min, triangular peak 50 to 300 uGy/h |
| Noise | multiplicative lognormal, sigma 0.1 |
| During `S5` | background × 1.5 while simulated ≥10 MeV flux ≥ 10 pfu (demo assumption) |
| Daily total target | 150 to 290 uGy/day (scale that day's SAA peaks if a day falls outside) |

**`dose_equivalent_rate` (uSv/h)** = absorbed × Q, Q uniform 2.0 to 2.5.

**Guardrail (V1 4033):** the generator's daily dose-equivalent total must stay well under 1.3 mSv/day (expected: about 0.3 to 0.7 mSv/day). A run that breaks this fails its test. This is a sanity check on the generator, **not** a comparison Pulsar shows users, because V1 4033 is a vehicle design value for free-space GCR in effective dose.

UI label: "Module dose equivalent rate (instrument reading, not personal dose)."

### 7b. `acceleration_quasi_steady` (micro-g)

Magnitude stored as `value`; axes in metadata (x mean 1.0 SD 0.2, y and z mean 0 SD 0.4). Venting transients every 2 to 3 days, 10 to 20 min, +3 to +4 micro-g on y and z. Band `< 0.01 Hz`. No limit in the listed documents, so display only. `acceleration_vibratory` stays out of MVP.

### 7c. `ppco2` (mmHg), cabin CO2 partial pressure

| Component | Spec |
|---|---|
| Nominal level | per-mission baseline uniform 1.8 to 2.2 |
| Daily pattern | +0.3 during crew wake hours (07:00 to 21:30 UTC), +0.2 extra during two 1-hour exercise blocks, −0.2 during sleep |
| Noise | normal, SD 0.08 |
| Clip | 1.0 to 9.0 (TB-004 historical ISS range) |
| `S6` excursion | Day 12, 10:00: linear rise to 4.0 over 6 h, hold 2 h, recover to nominal over 4 h |
| Checks | 1-hour means stay ≤ 3.0 outside `S6`; 7-day means stay < 2.5 for the whole mission, so only the 1-hour label fires in the demo |

`instrument = sim-co2-monitor`, `location_context = US Lab (simulated)`.

### 7d. `proton_flux_ge10mev` (pfu), NOAA-style space weather

| Component | Spec |
|---|---|
| Background | lognormal, median 0.3 pfu, sigma 0.3 (demo assumption, below S1) |
| `S5` storm | Day 27, 06:00: log-linear rise to 180 pfu (S2) over 6 h, then exponential decay, e-folding 12 h, back under 10 pfu on day 28 |
| Location | `Geostationary orbit (GOES-like, simulated)` |
| Event row | `mission_events`: `event_type = S_SCALE`, `level = S2`, start = first 5-min value ≥ 10 pfu, end = last value ≥ 10 pfu, `source = synthetic` |

The S-level is derived with the same thresholds as live NOAA data (section 2), so demo and live mode share code.

### 7e. Common fields

`source = synthetic`, `is_simulated = true`, `is_stale = false` (except `S7`), `source_retrieved_at = recorded_at`, `metadata = {"generator_version": "synth-0.2.0", "modeled_on": "...", "component": "background|saa|event|nominal|excursion"}`. Instruments: `sim-dosimeter`, `sim-accelerometer`, `sim-co2-monitor`, `sim-proton-monitor`.

## 8. Flag rules

Two separate kinds of flags, never merged into one score.

**Crew health flags (personal baseline, from `/analyze`):**
- Baseline: rolling 14-day median per indicator; at least 7 check-ins, otherwise `insufficient_data`.
- Score with Isolation Forest on deviations from the person's own baseline; explain with per-indicator observed vs baseline.
- No official or medical thresholds. Environment readings are not model inputs.

**Environment status labels (official limits, computed by the API from telemetry):**

| Label | Rule | Source |
|---|---|---|
| `ppco2_above_1h_limit` | rolling 1-hour mean ppCO2 > 3.0 mmHg | V2 6004 |
| `ppco2_above_7d_guidance` | rolling 7-day mean ppCO2 ≥ 2.5 mmHg | TB-004 guidance |
| `solar_storm_S1` to `S5` | 5-minute ≥10 MeV flux at the S-scale thresholds | NOAA S-scale |
| (none for radiation dose) | No published alert value | V2 6164 |

Environment labels appear on the mission-context panel with their source, never on a crew member's flag explanation.

## 9. Not modeled

- **Bone mineral density.** The brief states no system measures bone density in flight; requirements are pre- and post-mission DXA (pre-mission T-score ≥ −1.0; countermeasures keep hip and spine at or above 95% of pre-mission values and the femoral neck at or above 90%). Simulating in-flight BMD would invent a measurement that does not exist operationally.
- **Personal radiation dose against the 600 mSv career or 250 mSv SPE limits.** Needs personal effective dose, which a module reading is not.
- **Organ-specific short-term radiation limits.** Not in the current brief.

## 10. Output and loading

- Generator writes `crew_profiles.csv`, `health_checkins.csv`, `environment_readings.csv`, `mission_events.csv` and `synthetic_manifest.json` to `apps/api/app/synthetic/out/` (git-ignored).
- Saved real samples for live-mode adapters go in `apps/api/app/providers/samples/` (committed, small, with retrieval date): one DONKI SEP response and one NOAA `integral-protons-1-day.json`. See `docs/data-sources.md`.
- Same seed must produce byte-identical files; add a test, plus tests for the guardrail and checks in sections 7a and 7c.
- Seed 2026 produces 173 check-ins (CREW-D has only 5 days by design), 86,040 environment readings (5 series × 17,280, minus the 72-sample S7 gap each) and 2 simulated events.

## 11. Implementation notes (synth-0.2.0)

Choices made where the spec above was open. Change them here and in code together, and bump the version.

- **Days** are 1-indexed: day 1 = `2026-09-01`. Scenario day ranges are inclusive.
- **S1 mood:** on top of the sleep coupling, latent mood gets an extra −0.5 at the deepest point of the decline (scaled with it), so the mood change is visible on a 1 to 5 integer scale.
- **S2** ends abruptly after day 49 (no recovery ramp). RHR reaches the +10 cap on day 48.
- **`scenario_id`** in `data_quality` is the scenario active that day for that profile (`S4_schedule_shift` on days 20 and 21), otherwise `S0_stable`. `data_quality.mission_day` is also stored.
- **Key windows** (no missing rows, no null fields): S4 days for everyone, S1 36 to 55, S2 42 to 49, all of CREW-D.
- **IDs** are UUIDv5 from generator version, seed, table and natural key, so they are stable per seed.
- **Q factor** for dose equivalent is drawn once per day. SAA passes are 15-minute triangles sampled at the 5-minute grid; no day needed SAA rescaling with seed 2026.
- **Venting transients** are every 2 to 3 days, 10/15/20 minutes, the same offset added to y and z.
- **ppCO2 exercise blocks** are 09:00 to 10:00 and 16:00 to 17:00 UTC.
- **S5 storm** flux = max(background, storm curve × lognormal noise σ 0.1). Event start and end come from the generated values, using the shared `s_scale_level()` in `app/limits.py`.
- **S6 event** (`CO2_EXCURSION`, `level = ppco2_above_1h_limit`) spans the trailing 1-hour mean above 3.0 mmHg.
- **S7** removes 12:00 to 18:00 UTC on day 33 from all five series and marks the last reading before the gap (11:55) `is_stale = true`, with `metadata.feed_gap_until`.
- **CSV format:** Postgres `COPY`-ready: empty field = NULL, `true`/`false`, jsonb columns as compact JSON with sorted keys, timestamps `YYYY-MM-DDTHH:MM:SSZ`.

## Sources

- NASA-STD-3001 Vol 1 Rev C: https://standards.nasa.gov/sites/default/files/standards/NASA/C//nasa-std-3001-vol-1-rev-c-signature.pdf
- OCHMO-TB-020 Design for Ionizing Radiation Protection: https://www.nasa.gov/sites/default/files/atoms/files/radiation_protection_technical_brief_ochmo.pdf
- OCHMO-TB-004 Carbon Dioxide: https://www.nasa.gov/ochmo-tb-004-carbon-dioxide-2/
- Bone loss brief: https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-030-bone-loss.pdf
- NOAA S-scale definition: https://glossarystaging.ametsoc.net/wiki/S-scale
- NOAA solar radiation storm start/end: https://webarchive.library.unt.edu/web/20170119080503/http://www.swpc.noaa.gov/phenomena/solar-radiation-storm
- NOAA GOES proton flux product and JSON: https://www.spaceweather.gov/products/goes-proton-flux
- DONKI web services: https://ccmc.gsfc.nasa.gov/tools/DONKI
- Barger et al. 2014, astronaut sleep: https://pmc.ncbi.nlm.nih.gov/articles/PMC4188436
- Barger 2017 slides: https://vtti.whos.prod.es.cloud.vt.edu/PDFs/fatigue-2017/thursday-am/keynote/Barger.pdf
- Cardiovascular regulation on long ISS missions: https://phys.org/news/2012-03-benefits-space.pdf
- DOSIS 3D / DOSTEL: https://core.ac.uk/download/84275623.pdf
- R3D ISS dose by source: https://pmc.ncbi.nlm.nih.gov/articles/PMC3371259
- SAA dose rate map: https://www.swsc-journal.org/articles/swsc/full_html/2017/01/swsc160046/F9.html
- RadLab data API: https://visualization.osdr.nasa.gov/radlab/gui/data-api
- PIMS quasi-steady measurements: https://corpora.tika.apache.org/base/docs/govdocs1/116/116835.pdf
- NASA acceleration environment guide: https://www.nasa.gov/wp-content/uploads/2016/06/acceleration-environment-iss-mini-book_detail-508c.pdf
- LSDA data requests: https://nlsp.nasa.gov/explore/lsdahome/datarequest
- Inspiration4 in OSDR: https://pmc.ncbi.nlm.nih.gov/articles/PMC11094041
