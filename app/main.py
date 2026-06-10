from fastapi import FastAPI

from app.api.graph_auth import router as graph_auth_router
from app.api.graph_notifications import router as graph_notifications_router
from app.api.health import router as health_router
from app.api.teams import router as teams_router
from app.services.pii_redaction import setup_logging

app = FastAPI(
    title="HireSignal API",
    version="0.1.0",
    description="Backend for the HireSignal Microsoft 365 Copilot enterprise agent.",
)


@app.on_event("startup")
async def startup_event() -> None:
    """Set up logging with PII redaction on app startup."""
    try:
        from app.core.config import get_settings
        settings = get_settings()
        setup_logging(settings.log_level)
    except Exception:
        # If settings fail to load in test environment, use default logging
        setup_logging("INFO")


app.include_router(health_router)
app.include_router(graph_auth_router, prefix="/graph", tags=["graph"])
app.include_router(graph_notifications_router, prefix="/graph", tags=["graph"])
app.include_router(teams_router, prefix="/teams", tags=["teams"])


