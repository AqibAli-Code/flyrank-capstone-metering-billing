# Evidence

## Idempotent metering (Probe 1)
First call creates the event; second call with the same Idempotency-Key returns the identical event_id.

First call:
```json
// HTTP 200
{"status": "ok", "event_id": "726ec378-2f3b-4b77-a6a2-6719ef7b094e", "idempotent_replay": false}
```

Second call (same key):
```json
// HTTP 200
{"status": "ok", "event_id": "726ec378-2f3b-4b77-a6a2-6719ef7b094e", "idempotent_replay": true}
```

Automated test: tests/test_metering.py::test_duplicate_idempotency_key_returns_same_event — PASSED

## Quota boundary enforcement (Probe 2)
Tenant seeded at 98,950/100,000 ai_tokens. Call landing exactly at 100,000 → 200 OK. Next call → 429.

At boundary:
```json
// HTTP 200
{"status": "ok", "event_id": "b14fa189-e41c-4b92-8f12-3a58cf9e2b11", "idempotent_replay": false}
```

Over boundary:
```json
// HTTP 429
{"detail": {"error": "quota_exceeded", "message": "Monthly ai_tokens quota of 100000 exceeded.", "used": 101050, "limit": 100000}}
```

## Stripe subscription integration (Probe 3)
Real Checkout session completed with test card 4242 4242 4242 4242. Webhook flipped tenant Free → Pro.

Webhook log:
```text
2026-08-22 23:10:00   [200] POST http://localhost:8000/webhooks/stripe [evt_1U7IfVPP7vSlrVF2MmTPWgVX checkout.session.completed]
```
Database confirmation:
```text
tenant_id                            | plan_id | status | stripe_subscription_id     
--------------------------------------+---------+--------+----------------------------
88ca6f34-a73c-4ede-9ade-5312a93a600c  | pro     | active | sub_1U7IfVPP7vSlrVF2MmTPWgVX
```


## Webhook security (Probe 4)
Forged signature rejected:
```json
// HTTP 400
{"detail": "Invalid signature"}
```
Automated test: `tests/test_webhooks.py::test_forged_signature_rejected` — PASSED

Duplicate event ignored on replay:
```text
Stripe CLI event resend: evt_1U7IfVPP7vSlrVF2MmTPWgVX -> [200 OK]
Second delivery response body: {"status": "duplicate_ignored"}
```


## AI-token pricing (Probe 5)
tests/test_pricing.py::test_zero_usage_costs_zero — PASSED

tests/test_pricing.py::test_cached_input_cheaper_than_fresh_input — PASSED

tests/test_pricing.py::test_reasoning_tokens_bill_at_output_rate — PASSED

tests/test_pricing.py::test_categories_are_not_simply_summed_before_pricing — PASSED

tests/test_pricing.py::test_exact_pinned_total — PASSED

tests/test_pricing.py::test_missing_keys_default_to_zero — PASSED


## Full test suite
```text
python -m pytest -v

============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\user1\Desktop\flyrank-capstone-metering-billing
plugins: anyio-4.14.2, asyncio-1.4.0
collected 8 items

tests/test_metering.py::test_duplicate_idempotency_key_returns_same_event PASSED
tests/test_pricing.py::test_zero_usage_costs_zero PASSED
tests/test_pricing.py::test_cached_input_cheaper_than_fresh_input PASSED
tests/test_pricing.py::test_reasoning_tokens_bill_at_output_rate PASSED
tests/test_pricing.py::test_categories_are_not_simply_summed_before_pricing PASSED
tests/test_pricing.py::test_exact_pinned_total PASSED
tests/test_pricing.py::test_missing_keys_default_to_zero PASSED
tests/test_webhooks.py::test_forged_signature_rejected PASSED

============================== 8 passed in 0.99s ==============================
```