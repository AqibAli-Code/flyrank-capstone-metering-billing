from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import UsageEvent, Subscription, Plan


async def get_monthly_usage(db: AsyncSession, tenant_id: str, usage_type: str, period_start) -> int:
    result = await db.scalar(
        select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.usage_type == usage_type,
            UsageEvent.created_at >= period_start,
        )
    )
    return result


async def check_and_reserve_quota(db: AsyncSession, tenant, event: UsageEvent):
    sub = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    if sub is None:
        raise HTTPException(status_code=402, detail={"error": "no_subscription", "message": "Tenant has no active subscription."})

    plan = await db.get(Plan, sub.plan_id)

    if sub.status in ("past_due", "canceled"):
        raise HTTPException(
            status_code=402,
            detail={"error": "payment_required", "message": "Subscription is not active. Update billing to continue."},
        )

    limit = plan.ai_token_limit if event.usage_type == "ai_tokens" else plan.api_call_limit
    used = await get_monthly_usage(db, tenant.id, event.usage_type, sub.current_period_start)

    # Boundary rule (documented explicitly): usage AT the limit is allowed;
    # the request that would push usage OVER the limit is rejected.
    if used > limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "quota_exceeded",
                "message": f"Monthly {event.usage_type} quota of {limit} exceeded.",
                "used": used,
                "limit": limit,
            },
        )