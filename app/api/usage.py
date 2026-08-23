# app/api/usage.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_tenant
from app.db.models import Tenant, Subscription, Plan, UsageEvent
from app.pricing.config import calculate_token_cost

router = APIRouter()


@router.get("/usage")
async def get_usage(db: AsyncSession = Depends(get_db), tenant: Tenant = Depends(get_current_tenant)):
    sub = await db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
    plan = await db.get(Plan, sub.plan_id)

    events = await db.scalars(
        select(UsageEvent).where(
            UsageEvent.tenant_id == tenant.id,
            UsageEvent.usage_type == "ai_tokens",
            UsageEvent.created_at >= sub.current_period_start,
        )
    )
    events = events.all()

    total_cost = sum(calculate_token_cost(e.metadata_ or {}) for e in events)
    used_tokens = sum(e.quantity for e in events)

    return {
        "plan": plan.id,
        "ai_tokens": {"used": used_tokens, "limit": plan.ai_token_limit},
        "cost_micro_cents": total_cost,
    }