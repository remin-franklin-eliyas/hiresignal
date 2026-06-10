from pydantic import SecretStr

from app.core.config import Settings


def test_settings_build_graph_authority_and_scope_list() -> None:
    settings = Settings(
        GRAPH_TENANT_ID="tenant-id",
        GRAPH_CLIENT_ID="client-id",
        GRAPH_CLIENT_SECRET=SecretStr("secret"),
        GRAPH_SCOPES="https://graph.microsoft.com/.default, custom.scope",
        GRAPH_WEBHOOK_CLIENT_STATE=SecretStr("client-state"),
        GRAPH_MONITORED_USER_ID="recruiter@example.com",
        AZURE_AI_FOUNDRY_API_KEY=SecretStr("foundry-key"),
    )

    assert settings.graph_authority == "https://login.microsoftonline.com/tenant-id"
    assert settings.graph_scope_list == ["https://graph.microsoft.com/.default", "custom.scope"]
