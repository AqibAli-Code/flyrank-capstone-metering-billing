from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.api.generate import router as generate_router

app = FastAPI(title="Usage Metering & Billing Engine")
app.include_router(generate_router)


@app.get("/health")
async def health():
    return {"status": "ok"}