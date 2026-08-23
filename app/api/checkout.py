import os
import stripe
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_tenant
from app.db.models import Tenant, Plan

router = APIRouter()
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]


@router.post("/checkout/pro")
async def create_checkout_session(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
):
    # Stripe Customers are created lazily, on first checkout.
    if tenant.stripe_customer_id is None:
        customer = stripe.Customer.create(name=tenant.name, metadata={"tenant_id": str(tenant.id)})
        tenant.stripe_customer_id = customer.id
        await db.commit()

    plan = await db.get(Plan, "pro")

    session = stripe.checkout.Session.create(
        customer=tenant.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url="http://localhost:8000/checkout/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="http://localhost:8000/checkout/cancel",
        metadata={"tenant_id": str(tenant.id)},
    )
    return {"checkout_url": session.url}