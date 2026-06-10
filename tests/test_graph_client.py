import base64

import httpx
import pytest

from app.core.config import Settings
from app.services.graph_client import GraphClient, GraphClientError


class StubAuth:
    def acquire_app_token(self):
        return type(
            "Token",
            (),
            {"token_type": "Bearer", "access_token": "token"},
        )()


def build_settings() -> Settings:
    return Settings(
        GRAPH_TENANT_ID="tenant-id",
        GRAPH_CLIENT_ID="client-id",
        GRAPH_CLIENT_SECRET="secret",
        GRAPH_WEBHOOK_CLIENT_STATE="client-state",
        GRAPH_MONITORED_USER_ID="recruiter@example.com",
    )


@pytest.mark.asyncio
async def test_graph_client_lists_message_attachments() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert (
            request.url.path
            == "/v1.0/users/recruiter@example.com/messages/message-1/attachments"
        )
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "id": "attachment-1",
                        "name": "cv.pdf",
                        "size": 4,
                        "isInline": False,
                        "contentBytes": base64.b64encode(b"%PDF").decode("ascii"),
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://graph.test")
    graph_client = GraphClient(build_settings(), StubAuth(), http_client=client)

    attachments = await graph_client.list_message_attachments("recruiter@example.com", "message-1")

    assert attachments[0].name == "cv.pdf"
    assert attachments[0].decoded_content() == b"%PDF"


@pytest.mark.asyncio
async def test_graph_client_raises_after_http_failure() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "forbidden"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://graph.test")
    graph_client = GraphClient(build_settings(), StubAuth(), http_client=client)

    with pytest.raises(GraphClientError):
        await graph_client.list_message_attachments("recruiter@example.com", "message-1")
