from typing import Annotated

from fastapi import APIRouter, Query, status
from fastapi.responses import PlainTextResponse, Response

from app.models.notifications import ChangeNotificationCollection
from app.pipeline.ingestion import IngestionResult, get_outlook_ingestion_service

router = APIRouter()


@router.post("/notifications", response_model=None)
async def receive_graph_notifications(
    notifications: ChangeNotificationCollection | None = None,
    validation_token: Annotated[str | None, Query(alias="validationToken")] = None,
) -> Response | dict[str, list[IngestionResult]]:
    if validation_token is not None:
        return PlainTextResponse(content=validation_token, status_code=status.HTTP_200_OK)

    if notifications is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    ingestion_service = get_outlook_ingestion_service()
    results = await ingestion_service.process_notifications(notifications)
    return {"results": results}
