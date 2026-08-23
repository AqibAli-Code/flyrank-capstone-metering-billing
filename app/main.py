from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.api.generate import router as generate_router
from app.api.checkout import router as checkout_router
from app.api.webhooks import router as webhooks_router
from app.api.usage import router as usage_router  # 1. Import the usage router

app = FastAPI(title="Usage Metering & Billing Engine")
app.include_router(generate_router)
app.include_router(checkout_router)
app.include_router(webhooks_router)
app.include_router(usage_router)  # 2. Include the usage router


@app.get("/health")
async def health():
    return {"status": "ok"}