# tests/test_webhooks.py
import json
import time
import hmac
import hashlib
import os
import pytest


def _sign_payload(payload: bytes, secret: str) -> str:
    """Replicates Stripe's own signing scheme (t=timestamp,v1=hmac) so we can
    construct a validly-signed test event without hitting the real Stripe API."""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload.decode()}"
    signature = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


@pytest.mark.asyncio
async def test_forged_signature_rejected(client):
    r = await client.post("/webhooks/stripe", headers={"stripe-signature": "fake"}, content=b'{"fake": true}')
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_webhook_event_processed_once(client):
    secret = os.environ["STRIPE_WEBHOOK_SECRET"]
    payload_dict = {
        "id": "evt_test_dedup_pytest_001",
        "type": "ping.test.event",  # unhandled type — isolates dedup logic from business logic
        "data": {"object": {}},
    }