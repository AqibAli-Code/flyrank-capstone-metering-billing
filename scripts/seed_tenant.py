import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()

from app.db.database import async_session
from app.db.models import Tenant, Subscription

TENANT_ID = uuid.uuid4()

async def main():
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)

    async with async_session() as session:
        tenant = Tenant(id=TENANT_ID, name="Test Tenant")
        session.add(tenant)
        await session.flush()  # tenant row must exist before the FK below

        subscription = Subscription(
            tenant_id=tenant.id,
            plan_id="free",
            status="active",
            current_period_start=now,
            current_period_end=period_end,
        )
        session.add(subscription)
        await session.commit()

    print(f"Created tenant: {TENANT_ID}")
    print(f"Plan: free | Status: active | Period ends: {period_end.isoformat()}")
    print()
    print("Use this header in your requests:")
    print(f"  X-Tenant-Id: {TENANT_ID}")

if __name__ == "__main__":
    asyncio.run(main())