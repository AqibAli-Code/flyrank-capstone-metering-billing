# tests/conftest.py
import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import async_session
from app.db.models import Tenant, Subscription, UsageEvent


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seeded_tenant_id():
    tenant_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with async_session() as session:
        tenant = Tenant(id=tenant_id, name="Test Fixture Tenant")
        session.add(tenant)
        await session.flush()

        session.add(Subscription(
            tenant_id=tenant.id,
            plan_id="free",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        ))
        await session.commit()

    yield str(tenant_id)
    # No cleanup — deleting a tenant with usage_events would violate the FK
    # constraint (no ON DELETE CASCADE by design). Leftover test tenants in
    # the dev DB are harmless; not worth adding cascade logic for this capstone.


@pytest_asyncio.fixture
async def tenant_at_quota_boundary():
    """A tenant seeded exactly one /generate call away from its Free-plan limit."""
    tenant_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    plan_limit = 100_000
    call_tokens = 1050  # must match the token_usage total in app/api/generate.py
    baseline = plan_limit - call_tokens

    async with async_session() as session:
        tenant = Tenant(id=tenant_id, name="Quota Boundary Fixture Tenant")
        session.add(tenant)
        await session.flush()

        session.add(Subscription(
            tenant_id=tenant.id,
            plan_id="free",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        ))
        session.add(UsageEvent(
            tenant_id=tenant.id,
            usage_type="ai_tokens",
            quantity=baseline,
            idempotency_key="fixture-baseline",
            metadata_={"note": "seeded baseline for boundary testing"},
        ))
        await session.commit()

    yield str(tenant_id)
    # Same no-cleanup rationale as