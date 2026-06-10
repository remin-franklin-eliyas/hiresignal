from fastapi.testclient import TestClient

import app.api.graph_notifications as graph_notifications
from app.main import app
from app.pipeline.ingestion import IngestionResult


class StubIngestionService:
    async def process_notifications(self, notifications):
        return [
            IngestionResult(
                message_id=notifications.value[0].message_id,
                status="queued",
                accepted_attachments=1,
            )
        ]


def test_graph_webhook_validation_echoes_plain_text_token() -> None:
    client = TestClient(app)

    response = client.post("/graph/notifications?validationToken=opaque-token")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "opaque-token"


def test_graph_notification_endpoint_returns_ingestion_results(monkeypatch) -> None:
    monkeypatch.setattr(
        graph_notifications,
        "get_outlook_ingestion_service",
        lambda: StubIngestionService(),
    )
    client = TestClient(app)

    response = client.post(
        "/graph/notifications",
        json={
            "value": [
                {
                    "subscriptionId": "sub-1",
                    "clientState": "secret",
                    "changeType": "created",
                    "resource": "users/recruiter@example.com/messages/message-1",
                    "resourceData": {
                        "@odata.type": "#Microsoft.Graph.Message",
                        "id": "message-1",
                    },
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "queued"
