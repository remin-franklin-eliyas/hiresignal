from fastapi import FastAPI

from app.api.graph_auth import router as graph_auth_router
from app.api.graph_notifications import router as graph_notifications_router
from app.api.health import router as health_router

app = FastAPI(
    title="HireSignal API",
    version="0.1.0",
    description="Backend for the HireSignal Microsoft 365 Copilot enterprise agent.",
)

app.include_router(health_router)
app.include_router(graph_auth_router, prefix="/graph", tags=["graph"])
app.include_router(graph_notifications_router, prefix="/graph", tags=["graph"])
