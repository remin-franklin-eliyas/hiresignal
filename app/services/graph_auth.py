from collections.abc import Mapping
from typing import Any

import msal

from app.core.config import Settings, get_settings
from app.models.graph import GraphAccessToken


class GraphAuthError(RuntimeError):
    pass


class GraphAuthService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = msal.ConfidentialClientApplication(
            client_id=settings.graph_client_id,
            authority=settings.graph_authority,
            client_credential=settings.graph_client_secret.get_secret_value(),
        )

    def acquire_app_token(self) -> GraphAccessToken:
        result = self._client.acquire_token_silent(
            scopes=self._settings.graph_scope_list,
            account=None,
        )
        if not result:
            result = self._client.acquire_token_for_client(scopes=self._settings.graph_scope_list)

        return self._parse_token_result(result)

    @staticmethod
    def _parse_token_result(result: Mapping[str, Any]) -> GraphAccessToken:
        if "access_token" not in result:
            error = result.get("error", "unknown_error")
            description = result.get("error_description", "Microsoft Graph authentication failed.")
            raise GraphAuthError(f"{error}: {description}")

        return GraphAccessToken(
            access_token=str(result["access_token"]),
            token_type=str(result.get("token_type", "Bearer")),
            expires_in=int(result.get("expires_in", 0)),
            scope=result.get("scope"),
        )


def get_graph_auth_service() -> GraphAuthService:
    return GraphAuthService(get_settings())

