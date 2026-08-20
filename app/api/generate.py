from fastapi import APIRouter, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.metering import record_usage
from app.services.quota import check_and_reserve_quota
from app.dependencies import get_db, get_current_tenant
from app.db.models import Tenant

router = APIRouter()


@router.post("/generate")
async def generate(
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
):
    token_usage = {"input": 500, "cached_input": 200, "output": 300, "reasoning": 50}
    total_tokens = sum(token_usage.values())  # 1050 — quantity must match what quota checks against

    event, was_created = await record_usage(
        db, tenant.id, usage_type="ai_tokens", quantity=total_tokens,
        idempotency_key=idempotency_key,
        metadata=token_usage,
    )

    if not was_created:
        return {"status": "ok", "event_id": str(event.id), "idempotent_replay": True}

    await check_and_reserve_quota(db, tenant, event)

    return {"status": "ok", "event_id": str(event.id), "idempotent_replay": False}