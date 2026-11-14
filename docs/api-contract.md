# API contract

> Status: only `GET /health` is implemented. Types live in `apps/api/app/schemas.py`.

Base URL: `VITE_API_BASE_URL` (local: `http://localhost:8000`). Interactive docs: `/docs`.

## GET /health — implemented
Technical liveness check. Does not touch the database.

```json
200 OK
{ "status": "ok", "service": "pulsar-api", "demo_mode": true }
```

## POST /analyze — NOT implemented (returns 501)

Planned: analyse a check-in against the profile's personal baseline and return an explainable result.

### Request
```json
{
  "profile_id": "uuid",
  "checkin_id": "uuid | null"   // null → latest check-in (future behaviour)
}
```

### Current response
```json
501 Not Implemented
{ "detail": "POST /analyze is not implemented yet." }
```

### Planned response (future)
```json
200 OK
{
  "score": 0.0,
  "label": "within_baseline | worth_reviewing | insufficient_data",
  "explanation": "Plain-language summary for the astronaut.",
  "contributing_changes": [
    { "feature": "sleep_duration_hours", "observed": 5.1, "baseline": 7.2, "unit": "h" }
  ],
  "model_version": "string"
}
```

Planned behaviour (not built): load history from Supabase with the server key, compute baseline, score, write a row to `anomaly_results`. Output is decision support, not diagnosis.

### Planned auth
The browser will forward the user's Supabase JWT (`Authorization: Bearer …`); the API will verify it and check the caller owns `profile_id`.
