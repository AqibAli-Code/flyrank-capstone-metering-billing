import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()

from app.db.database import async_session
from app.db.models import Tenant, Subscription, UsageEvent

TENANT_ID = uuid.uuid4()
CALL_TOKENS = 1050        # matches the token_usage total in app/api/generate.py
PLAN_LIMIT = 100_000      # Free plan ai_token_limit
BASELINE = PLAN_LIMIT - CALL_TOKENS  # 98,950 — one call away from exactly at limit

async def main():
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)

    async with async_session() as session:
        tenant = Tenant(id=TENANT_ID, name="Quota Boundary Test Tenant")
        session.add(tenant)
        await session.flush()

        session.add(Subscription(
            tenant_id=tenant.id, plan_id="free", status="active",
            current_period_start=now, current_period_end=period_end,
        ))

        session.add(UsageEvent(
            tenant_id=tenant.id, usage_type="ai_tokens", quantity=BASELINE,
            idempotency_key="seed-baseline",
            metadata_={"note": "seeded baseline for boundary testing"},
        ))

        await session.commit()

    print(f"Tenant: {TENANT_ID}")
    print(f"Baseline usage: {BASELINE} tokens (limit is {PLAN_LIMIT})")
    print(f"Next /generate call ({CALL_TOKENS} tokens) will land EXACTLY at the limit → should succeed")
    print(f"The call after that will exceed it → should return 429")

if __name__ == "__main__":
    asyncio.run(main())