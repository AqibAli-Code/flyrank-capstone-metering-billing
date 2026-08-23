# tests/test_webhooks.py
import pytest

@pytest.mark.asyncio
async def test_forged_signature_rejected(client):
    r = await client.post("/webhooks/stripe", headers={"stripe-signature": "fake"}, content=b'{"fake": true}')
    assert r.status_code == 400