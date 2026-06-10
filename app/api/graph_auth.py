from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.graph import GraphTokenStatus
from app.services.graph_auth import GraphAuthError, GraphAuthService, get_graph_auth_service

router = APIRouter()


@router.get("/auth/status", response_model=GraphTokenStatus)
async def graph_auth_status(
    graph_auth: Annotated[GraphAuthService, Depends(get_graph_auth_service)],
) -> GraphTokenStatus:
    try:
        token = graph_auth.acquire_app_token()
    except GraphAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return GraphTokenStatus(
        authenticated=True,
        token_type=token.token_type,
        expires_in=token.expires_in,
        scope=token.scope,
    )
