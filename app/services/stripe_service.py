from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Tenant, Subscription


async def get_tenant_by_stripe_customer(db: AsyncSession, customer_id: str) -> Tenant | None:
    return await db.scalar(select(Tenant).where(Tenant.stripe_customer_id == customer_id))


async def get_subscription_by_stripe_id(db: AsyncSession, stripe_subscription_id: str) -> Subscription | None:
    return await db.scalar(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    )


async def get_or_create_subscription(db: AsyncSession, tenant_id) -> Subscription:
    sub = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant_id))
    if sub is None:
        sub = Subscription(tenant_id=tenant_id, plan_id="free", status="active",
                            current_period_start=None, current_period_end=None)
        db.add(sub)
        await db.flush()
    return sub