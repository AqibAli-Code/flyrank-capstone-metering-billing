import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.db.database import async_session
from app.db.models import Plan

PLANS = [
    Plan(
        id="free",
        name="Free",
        api_call_limit=1000,
        ai_token_limit=100_000,
        stripe_price_id=None,
    ),
    Plan(
        id="pro",
        name="Pro",
        api_call_limit=50_000,
        ai_token_limit=5_000_000,
        stripe_price_id="price_placeholder_pro",  # replace once you create it in Stripe test mode
    ),
]

async def main():
    async with async_session() as session:
        for plan in PLANS:
            await session.merge(plan)  # merge = insert or update, safe to re-run
        await session.commit()
    print(f"Seeded {len(PLANS)} plans: {[p.id for p in PLANS]}")

if __name__ == "__main__":
    asyncio.run(main())