from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import UsageEvent


async def record_usage(
    db: AsyncSession,
    tenant_id: str,
    usage_type: str,
    quantity: int,
    idempotency_key: str,
    metadata: dict | None = None,
) -> tuple[UsageEvent, bool]:
    """
    Returns (event, was_created).
    was_created=False means this exact (tenant, idempotency_key) pair was already
    recorded — a retry. Same event is returned, nothing new is written.
    """
    event = UsageEvent(
        tenant_id=tenant_id,
        usage_type=usage_type,
        quantity=quantity,
        metadata_=metadata,
        idempotency_key=idempotency_key,
    )
    db.add(event)
    try:
        await db.flush()
        await db.commit()
        return event, True
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(
            select(UsageEvent).where(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.idempotency_key == idempotency_key,
            )
        )
        return existing, False