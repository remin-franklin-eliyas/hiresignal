import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.models.attachments import GraphAttachmentCollection, GraphFileAttachment
from app.services.graph_auth import GraphAuthService, get_graph_auth_service


class GraphClientError(RuntimeError):
    pass


class GraphClient:
    def __init__(
        self,
        settings: Settings,
        graph_auth: GraphAuthService,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int = 3,
    ) -> None:
        self._settings = settings
        self._graph_auth = graph_auth
        self._http_client = http_client
        self._max_retries = max_retries

    async def list_message_attachments(
        self,
        user_id: str,
        message_id: str,
    ) -> list[GraphFileAttachment]:
        path = f"/users/{user_id}/messages/{message_id}/attachments"
        payload = await self._request("GET", path)
        return GraphAttachmentCollection.model_validate(payload).value

    async def _request(self, method: str, path: str) -> Mapping[str, Any]:
        url = f"{self._settings.graph_base_url.rstrip('/')}/{path.lstrip('/')}"
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=10)

        try:
            for attempt in range(self._max_retries):
                token = self._graph_auth.acquire_app_token()
                response = await client.request(
                    method,
                    url,
                    headers={"Authorization": f"{token.token_type} {token.access_token}"},
                )

                if response.status_code == 429 or 500 <= response.status_code < 600:
                    if attempt < self._max_retries - 1:
                        await self._sleep_before_retry(response)
                        continue

                if response.status_code == 401 and attempt < self._max_retries - 1:
                    continue

                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise GraphClientError(
                        f"Microsoft Graph request failed: {response.status_code}"
                    ) from exc
                return response.json()
        finally:
            if owns_client:
                await client.aclose()

        raise GraphClientError("Microsoft Graph request failed after retry attempts.")

    @staticmethod
    async def _sleep_before_retry(response: httpx.Response) -> None:
        retry_after = response.headers.get("Retry-After")
        delay_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 1
        await asyncio.sleep(delay_seconds)


def get_graph_client() -> GraphClient:
    return GraphClient(get_settings(), get_graph_auth_service())
