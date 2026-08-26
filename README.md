# Usage Metering & Billing Engine

Backend service for FlyRank's capstone brief: idempotent usage metering, quota enforcement, AI-token cost calculation, and Stripe subscription billing.

## 🎥 Video Demonstration

Watch the complete end-to-end capstone demo (FastAPI generation, Stripe checkout, webhook verification, and usage tracking):
👉 [Watch Video Proof on Google Drive](https://drive.google.com/file/d/1Icu2CSApQmuUPLQNTqUHp_Nu6zwoVO9R/view?usp=sharing)


## Architecture

```
Client ─► POST /generate
  └─► MeterService.record(tenant, type, qty, idempotency_key)
      ├─ duplicate key? → return original result, no new event
      ├─ store usage_event
      └─► Quota Check ─► allowed (200) or limit exceeded (402 / 429)

GET /usage ◄── rollup(usage_events) → { used, limit, cost }

Stripe Checkout (test mode) ─► subscription created
Stripe ─signed webhook─► POST /webhooks/stripe
├─► verify signature (forged → 400)
├─► deduplicate event (replay → ignored)
├─► update tenant plan / status
└─► schedule background task: write audit_logs row (off the request path)
```


## Setup (from a clean machine)

1. `python -m venv venv && .\venv\Scripts\Activate.ps1`
2. `pip install -r requirements.txt`
3. `docker compose up -d` — starts Postgres on port 5433
4. `Copy-Item .env.example .env` and fill in real Stripe test-mode keys (`sk_test_...`)
5. `python -m scripts.init_db` — creates all tables
6. `python -m scripts.seed_plans` — seeds Free and Pro plans
7. `python -m scripts.seed_tenant` — creates a test tenant, prints its UUID
8. `uvicorn app.main:app --reload`
9. In a separate terminal: `stripe listen --forward-to localhost:8000/webhooks/stripe` — copy the printed `whsec_...` into `.env`, restart step 8

## Run tests
python -m pytest -v


12 tests: 6 pinned pricing-math tests, 1 idempotent-metering test, 3 quota-boundary tests (well-under, at-limit, over-limit), 1 forged-webhook rejection test, 1 duplicate-webhook-event test.

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/generate` | Billable action. Requires `X-Tenant-Id` and `Idempotency-Key` headers. |
| GET | `/usage` | Current-period usage, quota limit, and cost for the calling tenant. |
| POST | `/checkout/pro` | Creates a Stripe Checkout session for the Pro plan. |
| POST | `/webhooks/stripe` | Stripe webhook receiver — signature-verified, deduplicated. |
| GET | `/health` | Liveness check. |

## Design notes

- **Idempotency**: enforced at the database level via a `UNIQUE (tenant_id, idempotency_key)` constraint on `usage_events` — not application-level check-then-insert, which would race under concurrent retries.
- **Quota boundary rule**: usage *at* the limit is allowed; the request that would push usage *over* the limit is rejected with `429`.
- **Money**: stored and computed as integer micro-cents throughout; converted to display currency only at the API edge.
- **AI-token pricing**: cached input tokens are billed cheaper than fresh input; reasoning tokens bill at the output-token rate, not as a separate category. See `app/pricing/config.py` and its pinned tests.
- **Webhook safety**: two independent layers — Stripe signature verification (forged events → `400`) and a `processed_webhook_events` table keyed on Stripe's own `event.id` (replayed legitimate events → ignored, not reprocessed).
- **Background audit logging**: after a webhook is verified and processed (or recognized as a duplicate), the response is returned to Stripe immediately, and a separate audit-log write happens afterward via FastAPI's `BackgroundTasks` — using its own database session, so it never adds latency to Stripe's webhook response. Retries on transient failure with backoff; logs a clear error if all retries are exhausted, since the response has already been sent by that point.

## Known limitations (explicit non-goals for this capstone's scope)

- Tenant identification uses a simplified `X-Tenant-Id` header rather than real authentication.
- No invoicing, proration, or overage billing — out of scope per the brief's §7 realistic-scope guidance.
- No cascading delete from `tenants` to dependent tables; not needed for the core metering/billing flow.