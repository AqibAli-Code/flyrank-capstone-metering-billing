# tests/test_metering.py
import pytest

@pytest.mark.asyncio
async def test_duplicate_idempotency_key_returns_same_event(client, seeded_tenant_id):
    headers = {"X-Tenant-Id": seeded_tenant_id, "Idempotency-Key": "test-dup-key"}
    r1 = await client.post("/generate", headers=headers)
    r2 = await client.post("/generate", headers=headers)

    assert r1.json()["event_id"] == r2.json()["event_id"]
    assert r2.json()["idempotent_replay"] is True