from fastapi import FastAPI

from src.api.conversations import router as conversations_router
from src.api.metrics import router as metrics_router
from src.api.webhook import router as webhook_router

app = FastAPI(
    title="Atendimento WhatsApp",
    description="API de automação de atendimento via WhatsApp.",
    version="0.1.0",
)
app.include_router(webhook_router)
app.include_router(conversations_router)
app.include_router(metrics_router)


@app.get("/health", tags=["operational"])
def health() -> dict[str, str]:
    return {"status": "ok"}
