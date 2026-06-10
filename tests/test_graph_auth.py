import pytest

from app.models.graph import GraphAccessToken
from app.services.graph_auth import GraphAuthError, GraphAuthService


def test_parse_token_result_success() -> None:
    token = GraphAuthService._parse_token_result(
        {
            "access_token": "token",
            "token_type": "Bearer",
            "expires_in": 3599,
            "scope": "https://graph.microsoft.com/.default",
        }
    )

    assert token == GraphAccessToken(
        access_token="token",
        token_type="Bearer",
        expires_in=3599,
        scope="https://graph.microsoft.com/.default",
    )


def test_parse_token_result_raises_on_graph_error() -> None:
    with pytest.raises(GraphAuthError, match="invalid_client"):
        GraphAuthService._parse_token_result(
            {
                "error": "invalid_client",
                "error_description": "Bad client secret.",
            }
        )

