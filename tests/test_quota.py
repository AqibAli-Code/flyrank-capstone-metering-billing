import pytest


@pytest.mark.asyncio
async def test_well_under_boundary_is_allowed(client, seeded_tenant_id):
    """A tenant with no prior usage is comfortably under quota — request succeeds."""
    headers = {"X-Tenant-Id": seeded_tenant_id, "Idempotency-Key": "quota-well-under"}
    r = await client.post("/generate", headers=headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_call_at_exact_boundary_is_allowed(client, tenant_at_quota_boundary):
    """Usage landing EXACTLY at the limit is allowed, per the documented boundary rule."""
    headers = {"X-Tenant-Id": tenant_at_quota_boundary, "Idempotency-Key": "quota-at-limit"}
    r = await client.post("/generate", headers=headers)
    assert r.status_code == 200
    assert r.json()["idempotent_replay"] is False


@pytest.mark.asyncio
async def test_call_over_boundary_returns_429(client, tenant_at_quota_boundary):
    """The FIRST call lands exactly at the limit (allowed); the SECOND pushes over it (rejected)."""
    headers1 = {"X-Tenant-Id": tenant_at_quota_boundary, "Idempotency-Key": "quota-at-limit"}
    await client.post("/generate", headers=headers1)

    headers2 = {"X-Tenant-Id": tenant_at_quota_boundary, "Idempotency-Key": "quota-over-limit"}
    r2 = await client.post("/generate", headers=headers2)

    assert r2.status_code == 429
    assert r2.json()["detail"]["error"] == "quota_exceeded"