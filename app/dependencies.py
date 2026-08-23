from uuid import UUID
from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import async_session
from app.db.models import Tenant


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_current_tenant(
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    try:
        tenant_uuid = UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")

    tenant = await db.get(Tenant, tenant_uuid)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Unknown tenant")
    return tenant