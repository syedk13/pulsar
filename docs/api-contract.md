# API contract

> Status: `GET /health` and `POST /analyze` are implemented. Types live in `apps/api/app/schemas.py`.

Base URL: `VITE_API_BASE_URL` (local: `http://localhost:8000`). Interactive docs: `/docs`.

## GET /health
Technical liveness check. Does not touch the database or require auth.

```json
200 OK
{ "status": "ok", "service": "pulsar-api", "demo_mode": true }
```

## POST /analyze

Compares one check-in with the profile's own recent history, returns an explainable result and stores it in `anomaly_results`. Decision support only: it compares a person with themselves, is not trained or validated on astronaut medical data, and is not a diagnosis.

### Auth
- Header `Authorization: Bearer <Supabase access token>` of the signed-in user (the web app's `session.access_token`).
- The API asks Supabase Auth who the token belongs to (`GET /auth/v1/user`), then checks that `crew_profiles.user_id` for `profile_id` is that user.
- Missing, invalid, expired or revoked token → **401** (`WWW-Authenticate: Bearer`). Checked before the body, so a request with no token is 401 even with no body.
- Unknown profile, someone else's profile, or a `checkin_id` that is not in that profile → **404** `{"detail": "Profile or check-in not found."}` (the same answer for all three, so it reveals nothing).
- There is no `DEMO_MODE` bypass.
- Supabase not configured or unreachable → **503**.

### Request
```json
{
  "profile_id": "uuid",
  "checkin_id": "uuid | null"   // null or omitted → the profile's latest check-in
}
```
A body that is not valid (e.g. `profile_id` not a UUID) with a valid token → 422.

### Response `200 OK`
Real output for CREW-C, mission day 47 (seed 2026):
```json
{
  "checkin_id": "13c41df1-5239-5d8f-a5be-74709dc09d28",
  "score": 0.568967,
  "label": "worth_reviewing",
  "explanation": "This check-in differs from your usual pattern and is worth reviewing. Resting heart rate was 78 bpm, above your usual 63.5 bpm. Your usual = median of your last 14 check-ins (2026-10-02 to 2026-10-16, UTC). This compares you only with your own history; it is not validated on astronaut medical data and is not a diagnosis.",
  "contributing_changes": [
    { "feature": "resting_heart_rate", "observed": 78.0, "baseline": 63.5, "unit": "bpm", "basis": "this_checkin" }
  ],
  "model_version": "baseline-iforest-0.1.0"
}
```
- `checkin_id`: the check-in analysed. `null` only when the profile has no check-ins.
- `score`: Isolation Forest score in (0, 1), higher = more unusual. **`null` for `insufficient_data`.**
- `label`: `within_baseline` | `worth_reviewing` | `insufficient_data` (shown as "collecting baseline").
- `contributing_changes`: only for `worth_reviewing`, otherwise `[]`. `feature` is `sleep_duration_hours` (unit `h`), `resting_heart_rate` (`bpm`) or `mood_rating` (`score (1-5)`). `basis` is `this_checkin` (`observed` is this check-in's value) or `last_3_checkins` (`observed` is the average of this and the 2 check-ins before it). `baseline` is the median of the window.
- A profile with no check-ins returns `insufficient_data` with `checkin_id: null`, not an error.

### Baseline rule (decided)
- Baseline per indicator = median of the profile's **last 14 check-ins** before the one being scored, counted by check-in, not by calendar days. With the one-per-day cap, that is also the last 14 days that have a check-in.
- History includes every source (`synthetic` and `self_report`), so form check-ins build on the synthetic mission.
- Fewer than **7** earlier check-ins → `label: "insufficient_data"` ("collecting baseline"), no score.
- A field that is `null` in a check-in is skipped for that indicator, not treated as zero.
- **Per indicator:** an indicator with fewer than **7** non-null values in the window, or `null` in the scored check-in, is left out of the score and the explanation says so (e.g. "Mood was not recorded in this check-in, so it was not compared."). If no indicator can be compared, the result is `insufficient_data`.

### Features and model (`baseline-iforest-0.1.0`, `apps/api/app/ml/`)
- **Spread** per indicator = scaled MAD of the window (×1.4826, with the Croux & Rousseeuw small-sample correction for 7 to 14 values), never below a measurement-resolution floor: sleep 0.25 h, resting heart rate 2 bpm, mood 0.75 points. The floor stops a perfectly steady history (MAD 0) from turning a tiny change into a large deviation. These are not health thresholds.
- **Deviation** = (this check-in − median) / spread. **Trend** = (average of this and the 2 previous check-ins − median) / spread.
- **Model:** scikit-learn `IsolationForest` (200 trees, fixed `random_state`) over 6 features: [deviation, trend] × 3 indicators. An indicator that was left out counts as 0.
  - **How it is fit:** once, on a pooled reference of 4,000 simulated steady histories (independent noise, windows of 7 to 14, the same median/MAD/trend arithmetic). It is not fit per profile.
  - **Why pooled:** with only 7 to 14 baseline points, a per-profile forest isolates almost any point in 3 to 4 splits, so its scores carry little information. The personal part lives in the features (each person's own median and spread); the forest judges how unusual the combination of deviations is.
  - The reference contains no scenario data and no environment data. The same input always gives the same score.
- Environment readings are never inputs.

### Label rule
- `insufficient_data`: fewer than 7 earlier check-ins, or no indicator could be compared.
- `worth_reviewing`: at least one indicator differs from your usual (**≥ 2 spreads** for this check-in, or **≥ 1.5 spreads** for the last-3 average), **and** either:
  - the forest score is above the gate (more unusual than 92.5% of steady reference check-ins), or
  - one indicator changed very clearly on its own (≥ 3.5 spreads, or ≥ 3.0 for the last-3 average). This second path exists because a forest over 6 features scores a large change in a single feature only about 0.46, below the gate.

  The indicators that meet the first condition are the `contributing_changes`, so every flag names what changed.
- `within_baseline`: otherwise.

### Stored result (`anomaly_results`)
Every result is saved, including `insufficient_data`. Columns:
- `profile_id`
- `checkin_id` (null if the profile has no check-ins)
- `score` (null if there is no score)
- `review_label`
- `model_version`
- `explanation` (jsonb), which holds:
  - `text` and `contributing_changes`
  - `scored_checkin`
  - `window`: the rule, the number of check-ins, and the first and last timestamps
  - `indicators`: per indicator, its status, values in the window, observed, baseline, spread, deviation, trend and unit
  - `label_rule`: the thresholds used
  - `flag_path`: `combination`, `single_indicator`, or null
  - `not_validated`

**Re-analysis:**
- Analysing the same check-in again with the same `model_version` **replaces** the earlier row, so the latest analysis wins. It is a delete followed by an insert, so it is not atomic.
- For a profile with no check-ins, the row with `checkin_id` null is replaced the same way.
- A new `model_version` keeps the old rows alongside the new ones.

### Behaviour on the synthetic scenarios (seed 2026, `apps/api/tests/test_scenarios.py`)
| Profile | Expected (synthetic-data.md §6) | Actual with `baseline-iforest-0.1.0` |
|---|---|---|
| CREW-A `S0_stable` | `within_baseline` | 42 of 49 scored check-ins `within_baseline`. Flagged (sleep only): days 20 to 22 (S4 sleep dip), plus days 9 and 56 to 58, where the generated data happens to have low sleep |
| CREW-B `S1_sleep_decline` | `worth_reviewing` from about day 42 (sleep, mood) | First flag on **day 46** (resting heart rate and sleep), then day 47 (resting heart rate). Mood is never named. Two reasons: the rolling 14-check-in baseline moves down with a gradual decline, and 1-point mood steps stay within 2 spreads |
| CREW-C `S2_rhr_trend` | `worth_reviewing`, resting HR only | Days 45, 46 and 47, resting heart rate only |
| CREW-D `S3_new_profile` | `insufficient_data` | All 5 check-ins `insufficient_data` |

Sensitivity varies with the random seed. With seed 7, CREW-B is flagged only on day 55 and CREW-C only on day 48. Treat these results as one illustration, not a validation.
