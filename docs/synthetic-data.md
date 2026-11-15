# Synthetic data spec

> Status: spec only. No generator code exists yet. Target home: `apps/api/app/synthetic/`.

Everything here is **simulated demo data**. Ranges are shaped by published NASA and peer-reviewed figures (see Sources) but nothing is "NASA-calibrated." Never label a generated value as NASA data.

## 1. Source roles (decided)

| Source | Raw data we can ingest now? | Role in Pulsar | Do not |
|---|---|---|---|
| LSDA / Life Sciences Portal | **No.** Astronaut research data is released only after a data request, review and NASA IRB approval. | Background for which measures are credible (sleep, cardiovascular). Not used in the MVP. | Assume a public daily sleep, mood or RHR series exists. |
| OSDR (biological studies, incl. Inspiration4) | **No** for our use. Only processed data is public; raw individual data needs approval, and it is omics/clinical samples from a 3-day flight, not daily check-ins. | Out of MVP scope. | Present it as check-in data. |
| OSDR RadLab | **Yes, technically.** Public query API returning `absorbed_dose_rate`, `dose_equivalent_rate`, `flux` per instrument, module and timestamp. | Shape the synthetic radiation stream now. Optional later: cache one real day behind `app/providers/radlab.py`. | Treat module dose rate as a person's dose. Mix dose rate, dose equivalent and flux in one series. |
| NASA PIMS (MAMS, SAMS-II) | **Not practical.** Archives are high-rate raw sensor files in a time/sensor folder tree that need signal processing. | Shape the synthetic quasi-steady acceleration stream. | Imply acceleration measures a body's response. |
| DONKI | **Yes.** Simple JSON API (`FLR`, `SEP`, `CME`, `GST`, `RBE`, ...). | Optional event context ("SEP event during this interval"). Post-MVP. | Turn an event into a dose value. |
| Curiosity RAD | Public archive, but **wrong environment** (Mars surface). | Optional "Mars surface" scenario scaling only. | Use its values as ISS or astronaut dose. |
| NTRS | Documents, not data. | Evidence library for the Sources list and the pitch. | Expect telemetry. |

**Conclusion:** no public raw dataset fits daily crew check-ins. Health data is 100% synthetic. Environment data is synthetic, shaped by published ISS ranges. Live NASA adapters are optional post-MVP work (M7).

## 2. Schema changes needed

The current migration mostly fits. Keep the existing column names (`recorded_at`, `mood_rating`, `resting_heart_rate`); do not rename to other proposals like `checkin_at` or `mood_score`.

1. **Required: widen `environment_readings.measurement_type`.** Today it only allows `acceleration` and `radiation`, which would mix absorbed dose rate and dose equivalent rate in one type. New migration:

   ```sql
   alter table public.environment_readings
     drop constraint environment_readings_measurement_type_check;
   alter table public.environment_readings
     add constraint environment_readings_measurement_type_check
     check (measurement_type in (
       'acceleration_quasi_steady', 'acceleration_vibratory',
       'absorbed_dose_rate', 'dose_equivalent_rate', 'particle_flux'));
   ```
   Update `docs/data-model.md` in the same commit. (Check the real constraint name with `\d environment_readings` if the migration was applied with a different one.)

2. **No change to `health_checkins`.** Put generator metadata in the existing `data_quality` jsonb (section 4).

3. **Optional, post-MVP:** a `mission_events` table for DONKI-style events (`event_type`, `start_time`, `end_time`, `source`, `source_event_id`, `link`, `is_simulated`). Do not store events in `environment_readings`.

## 3. Mission frame

| Setting | Value |
|---|---|
| Seed | `2026` (one `numpy.random.default_rng(seed)`; derive per-profile streams with `rng.spawn`) |
| Mission length | 60 days |
| Mission start | `2026-09-01T00:00:00Z` (all timestamps UTC) |
| Mission label | `Pulsar Demo Mission (simulated)` |
| Generator version | `synth-0.1.0`, written into every row's metadata |

## 4. Daily crew check-ins (`health_checkins`)

One row per profile per day, `recorded_at` = day start + 07:00 UTC ± uniform 30 min (morning, on waking).

| Field | Type / unit | Per-profile baseline | Day-to-day noise | Clip | Rounding |
|---|---|---|---|---|---|
| `sleep_duration_hours` | hours, previous sleep period | uniform 5.6 to 7.0 | normal, SD 0.6 | 3.0 to 9.5 | 0.1 h |
| `resting_heart_rate` | bpm, morning resting | uniform 52 to 66 | normal, SD 2.5 | 40 to 110 | integer |
| `mood_rating` | 1 to 5 scale below | latent uniform 3.4 to 4.2 | normal, SD 0.5 | 1 to 5 | integer |

Couplings (demo assumptions, keep them weak so single-indicator flags stay explainable):
- RHR: +1 bpm per hour of sleep below the profile's sleep baseline.
- Mood (latent, before rounding): +0.3 per hour of sleep above baseline, −0.3 per hour below.

Why these ranges: in a large actigraphy study, ISS astronauts averaged about 6.1 h of sleep in flight despite 8.5 h scheduled, and sleep was about 1 h shorter when circadian timing was misaligned (5.4 vs 6.4 h). ISS cardiovascular studies found heart rate roughly unchanged from preflight, so RHR uses ordinary fit-adult values. Mood has **no** NASA calibration; it is our own scale.

**Mood scale** `pulsar-mood-1to5-v1` (show the anchors in the check-in UI):

| Value | Label |
|---|---|
| 1 | Very low |
| 2 | Low |
| 3 | Okay |
| 4 | Good |
| 5 | Very good |

**Fixed columns:** `source = 'synthetic'`, `is_simulated = true`.

**`data_quality` jsonb:**
```json
{
  "generator_version": "synth-0.1.0",
  "scenario_id": "S1_sleep_decline",
  "hr_kind": "resting_morning",
  "mood_scale": "pulsar-mood-1to5-v1",
  "missing_fields": []
}
```

**Missing data (deterministic from the seed):**
- 6% of days per profile have no row at all (skip days inside a scenario's key window so the demo stays clean).
- 2% of rows have one field set to `null`, listed in `missing_fields`.

## 5. Profiles and scenarios

| Profile | Scenario id | What happens | Expected `/analyze` result |
|---|---|---|---|
| `CREW-A` | `S0_stable` | Baseline only | `within_baseline` nearly every day |
| `CREW-B` | `S1_sleep_decline` | Days 36 to 50: sleep mean drops linearly by 1.5 h; mood follows via coupling; recovers days 51 to 55 | `worth_reviewing` from about day 42, explanation names sleep (and mood) |
| `CREW-C` | `S2_rhr_trend` | Days 42 to 49: RHR rises 1.5 bpm/day to +10 bpm, sleep unchanged | `worth_reviewing`, explanation names RHR only |
| `CREW-D` | `S3_new_profile` | Only the last 5 days of data exist | `insufficient_data` ("collecting baseline") |
| all | `S4_schedule_shift` | Days 20 and 21: sleep −1.0 h for everyone (modeled on the misalignment effect) | Short dip; good test that one or two bad nights are handled sensibly |

Use `display_name` values like `Crew A (fictional)`, `is_fictional = true`. Keep the true generator parameters in a manifest file (`synthetic_manifest.json`), **not** in `baseline_metadata`, so the model cannot read the answer key.

Baseline rule for the ML side (proposal, record the final choice in `api-contract.md`): rolling 14-day median per indicator, minimum 7 check-ins before scoring, otherwise `insufficient_data`.

## 6. Environment telemetry (`environment_readings`)

Separate stream, same mission clock, never joined into health rows. Sample every **5 minutes** (288 rows/day per series, about 17,000 per series for 60 days). Charts should show hourly mean and max.

### 6a. Radiation: `absorbed_dose_rate` (unit `uGy/h`)

Model = background + South Atlantic Anomaly (SAA) passes + noise.

| Component | Spec |
|---|---|
| Background (cosmic rays) | 2 to 6 uGy/h, sinusoid with the 92-minute orbit (latitude effect) |
| SAA passes | One block per day of 5 to 6 consecutive orbits crossing the SAA, each about 15 minutes; peak 50 to 300 uGy/h with a triangular shape. Outside the block, no SAA passes for the rest of the day |
| Noise | multiplicative, lognormal sigma 0.1 |
| Daily total target | 150 to 290 uGy/day (check after generating; scale peaks if outside) |
| Optional event | `S5_sep_context` days 27 to 28: background ×2 for 24 h, with a matching simulated event record if `mission_events` exists. Keep it away from the health scenario windows so the demo never suggests a cause |

Why: inside-ISS daily absorbed dose rates in the literature run roughly 74 to 215 uGy/day, Columbus DOSTEL readings reached 286 uGy/day, crew badges usually record under 0.3 mGy/day, and SAA protons cause most of the absorbed dose, with hourly rates spanning about 5 to 500 uGy/h.

### 6b. Radiation: `dose_equivalent_rate` (unit `uSv/h`)

Same timestamps as 6a. `value = absorbed × Q` with Q uniform 2.0 to 2.5 per sample (Columbus figures: 647 uSv/day equivalent vs 286 uGy/day absorbed, ratio about 2.3). Real Q differs by radiation source; constant-ish Q is a documented simplification.

Label in the UI: "Module dose equivalent rate (instrument reading, not personal dose)."

### 6c. Acceleration: `acceleration_quasi_steady` (unit `micro-g`)

| Component | Spec |
|---|---|
| Value stored | Vector magnitude in micro-g |
| Axes (in `metadata`) | x: mean 1.0, SD 0.2; y and z: mean 0, SD 0.4 (micro-g) |
| Typical magnitude | about 1.0 to 1.3 micro-g |
| Venting transient | every 2 to 3 days, 10 to 20 minutes, +3 to +4 micro-g on y and z |
| Frequency band (metadata) | `< 0.01 Hz` |

Why: PIMS reports put the ISS quasi-steady magnitude around 1.1 micro-g, with venting transients of 3 to 4 micro-g; NASA defines the quasi-steady regime as content below 0.01 Hz.

`acceleration_vibratory` (SAMS-like g-jitter, 0.01 to 300 Hz) is **out of MVP scope**. It needs frequency-band choices we have not sourced.

### 6d. Common environment fields

| Column | Value |
|---|---|
| `source` | `synthetic` |
| `instrument` | `sim-dosimeter` or `sim-accelerometer` (never a real instrument name on its own) |
| `location_context` | `US Lab (simulated)` / `Columbus (simulated)` |
| `is_simulated` | `true` |
| `is_stale` | `false`, except one 6-hour gap with `is_stale = true` on day 33 to demo freshness labels |
| `source_retrieved_at` | same as `recorded_at` |
| `metadata` | `{"generator_version": "synth-0.1.0", "modeled_on": "published ISS ranges, see docs/synthetic-data.md", "axes": {...}, "band": "<0.01 Hz", "component": "background|saa|event"}` |

## 7. Output and loading

- Generator writes `crew_profiles.csv`, `health_checkins.csv`, `environment_readings.csv` and `synthetic_manifest.json` to `apps/api/app/synthetic/out/` (git-ignored; regenerate from the seed).
- A seed script loads them into Supabase with the server key. Same seed must produce byte-identical files; add a test for that.
- Rows total: about 230 check-ins, about 52,000 environment readings (3 series).

## Sources

- Barger et al. 2014, sleep in astronauts (Lancet Neurology): https://pmc.ncbi.nlm.nih.gov/articles/PMC4188436
- Barger 2017 slides, aligned vs misaligned sleep: https://vtti.whos.prod.es.cloud.vt.edu/PDFs/fatigue-2017/thursday-am/keynote/Barger.pdf
- Cardiovascular regulation on long ISS missions (summary): https://phys.org/news/2012-03-benefits-space.pdf
- ISS crew dose standards review: https://pmc.ncbi.nlm.nih.gov/articles/PMC10919966
- DOSIS 3D / DOSTEL in Columbus: https://core.ac.uk/download/84275623.pdf
- R3D on ISS, SAA vs GCR dose: https://pmc.ncbi.nlm.nih.gov/articles/PMC3371259
- SAA dose rate map (5 to 500 uGy/h): https://www.swsc-journal.org/articles/swsc/full_html/2017/01/swsc160046/F9.html
- RadLab data API: https://visualization.osdr.nasa.gov/radlab/gui/data-api
- PIMS quasi-steady measurements: https://corpora.tika.apache.org/base/docs/govdocs1/116/116835.pdf
- NASA acceleration environment guide: https://www.nasa.gov/wp-content/uploads/2016/06/acceleration-environment-iss-mini-book_detail-508c.pdf
- PIMS archive structure: https://ntrs.nasa.gov/api/citations/20120012936/downloads/20120012936.pdf
- DONKI web services: https://ccmc.gsfc.nasa.gov/tools/DONKI
- LSDA data requests: https://nlsp.nasa.gov/explore/lsdahome/datarequest
- Inspiration4 data in OSDR: https://pmc.ncbi.nlm.nih.gov/articles/PMC11094041
- Curiosity RAD surface dose (Hassler et al. 2014): https://ntrs.nasa.gov/citations/20180007641
