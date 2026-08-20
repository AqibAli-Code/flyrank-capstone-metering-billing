## Idempotent metering (Probe 1)
Duplicate request with same Idempotency-Key returns identical event_id; second call returns idempotent_replay: true.

First call — creates the event:
```json
// HTTP 200
{
  "status": "ok",
  "event_id": "726ec378-2f3b-4b77-a6a2-6719ef7b094e",
  "idempotent_replay": false
}
```

Second call — same Idempotency-Key, same event_id returned, no new event created:
```json
// HTTP 200
{
  "status": "ok",
  "event_id": "726ec378-2f3b-4b77-a6a2-6719ef7b094e",
  "idempotent_replay": true
}
```

## Quota boundary enforcement (Probe 2)
Tenant seeded at 98,950/100,000 ai_tokens. Call landing exactly at 100,000 → 200 OK. Next call → 429 quota_exceeded.

Call at the exact boundary (98,950 + 1,050 = 100,000) — allowed:
```json
// HTTP 200
{
  "status": "ok",
  "event_id": "PASTE_REAL_EVENT_ID_HERE",
  "idempotent_replay": false
}
```

Call after the boundary (100,000 + 1,050 = 101,050) — rejected:
```json
// HTTP 429
{
  "detail": {
    "error": "quota_exceeded",
    "message": "Monthly ai_tokens quota of 100000 exceeded.",
    "used": 101050,
    "limit": 100000
  }
}
```