import os
import stripe
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.db.models import ProcessedWebhookEvent
from app.services.stripe_service import (
    get_tenant_by_stripe_customer,
    get_subscription_by_stripe_id,
    get_or_create_subscription,
)
from app.services.audit import log_webhook_processed

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Layer 1: cryptographic signature verification — forgeries get 400.
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Layer 2: dedup on Stripe's own event.id via unique constraint —
    # insert-first, same pattern as usage-event idempotency in Phase 2.
    record = ProcessedWebhookEvent(stripe_event_id=event["id"], event_type=event["type"])
    db.add(record)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        background_tasks.add_task(log_webhook_processed, event["id"], event["type"], "duplicate_ignored")
        return {"status": "duplicate_ignored"}

    await handle_event(db, event)
    await db.commit()
    background_tasks.add_task(log_webhook_processed, event["id"], event["type"], "processed")
    return {"status": "processed"}


async def handle_event(db: AsyncSession, event: dict):
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await activate_pro_subscription(db, customer_id=data["customer"], subscription_id=data["subscription"])

    elif event_type == "customer.subscription.updated":
        await sync_subscription_from_stripe(db, data)

    elif event_type == "customer.subscription.deleted":
        await downgrade_to_free(db, stripe_subscription_id=data["id"])
    # Any other event type is acknowledged (200 via the return in stripe_webhook) but ignored.


async def activate_pro_subscription(db: AsyncSession, customer_id: str, subscription_id: str):
    tenant = await get_tenant_by_stripe_customer(db, customer_id)
    if tenant is None:
        return

    sub = await get_or_create_subscription(db, tenant.id)

    stripe_sub = stripe.Subscription.retrieve(subscription_id)
    period_item = stripe_sub["items"]["data"][0]  # period now lives on the subscription item, not the subscription itself

    sub.plan_id = "pro"
    sub.status = "active"
    sub.stripe_subscription_id = subscription_id
    sub.current_period_start = datetime.fromtimestamp(period_item["current_period_start"], tz=timezone.utc)
    sub.current_period_end = datetime.fromtimestamp(period_item["current_period_end"], tz=timezone.utc)
    await db.flush()


async def sync_subscription_from_stripe(db: AsyncSession, stripe_sub_data: dict):
    sub = await get_subscription_by_stripe_id(db, stripe_sub_data["id"])
    if sub is None:
        return

    period_item = stripe_sub_data["items"]["data"][0]

    sub.status = stripe_sub_data["status"]
    sub.current_period_start = datetime.fromtimestamp(period_item["current_period_start"], tz=timezone.utc)
    sub.current_period_end = datetime.fromtimestamp(period_item["current_period_end"], tz=timezone.utc)
    await db.flush()


async def downgrade_to_free(db: AsyncSession, stripe_subscription_id: str):
    sub = await get_subscription_by_stripe_id(db, stripe_subscription_id)
    if sub is None:
        return
    sub.plan_id = "free"
    sub.status = "canceled"
    await db.flush()