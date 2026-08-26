import asyncio
import logging
from app.db.database import async_session
from app.db.models import AuditLog

logger = logging.getLogger("audit")


async def log_webhook_processed(stripe_event_id: str, event_type: str, status: str, max_retries: int = 3):
    """
    Background job: writes an audit-trail row for a processed webhook event.

    Runs AFTER the HTTP response has already been sent back to Stripe — using
    its OWN database session, since the request's session is closed by the
    time this executes. This keeps the audit write off Stripe's webhook
    response-time budget (slow/bulk work off the request path).

    Retries on transient DB failure with linear backoff. If all retries are
    exhausted, this can't raise back to the original caller (the response
    already went out), so it logs a clearly-marked failure alert instead.
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            async with async_session() as session:
                session.add(AuditLog(
                    event_type=event_type,
                    reference_id=stripe_event_id,
                    status=status,
                    detail=f"Logged on attempt {attempt}",
                ))
                await session.commit()
            return  # success
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.5 * attempt)

    logger.error(
        "AUDIT LOG WRITE FAILED after %s attempts for event %s (%s): %s",
        max_retries, stripe_event_id, event_type, last_error,
    )