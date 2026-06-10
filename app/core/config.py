from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="local", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    graph_tenant_id: str = Field(alias="GRAPH_TENANT_ID")
    graph_client_id: str = Field(alias="GRAPH_CLIENT_ID")
    graph_client_secret: SecretStr = Field(alias="GRAPH_CLIENT_SECRET")
    graph_scopes: str = Field(
        default="https://graph.microsoft.com/.default",
        alias="GRAPH_SCOPES",
    )
    graph_base_url: str = Field(default="https://graph.microsoft.com/v1.0", alias="GRAPH_BASE_URL")
    graph_webhook_client_state: SecretStr = Field(alias="GRAPH_WEBHOOK_CLIENT_STATE")
    graph_monitored_user_id: str = Field(alias="GRAPH_MONITORED_USER_ID")

    azure_ai_foundry_endpoint: str | None = Field(default=None, alias="AZURE_AI_FOUNDRY_ENDPOINT")
    azure_ai_foundry_api_key: SecretStr | None = Field(
        default=None,
        alias="AZURE_AI_FOUNDRY_API_KEY",
    )
    azure_ai_foundry_model: str = Field(default="gpt-4.1-mini", alias="AZURE_AI_FOUNDRY_MODEL")
    use_local_scoring_fallback: bool = Field(default=True, alias="USE_LOCAL_SCORING_FALLBACK")

    database_url: str = Field(default="sqlite:///./hiresignal.local.sqlite3", alias="DATABASE_URL")
    pipeline_version: str = Field(default="2026.06.10", alias="PIPELINE_VERSION")
    job_rubric_path: Path = Field(
        default=Path("config/job_rubric.sample.json"),
        alias="JOB_RUBRIC_PATH",
    )
    teams_channel_id: str | None = Field(default=None, alias="TEAMS_CHANNEL_ID")
    fabric_workspace_id: str | None = Field(default=None, alias="FABRIC_WORKSPACE_ID")
    fabric_lakehouse_id: str | None = Field(default=None, alias="FABRIC_LAKEHOUSE_ID")
    fabric_audit_mode: str = Field(default="sqlite", alias="FABRIC_AUDIT_MODE")
    fabric_audit_endpoint: str | None = Field(default=None, alias="FABRIC_AUDIT_ENDPOINT")
    fabric_audit_token: SecretStr | None = Field(default=None, alias="FABRIC_AUDIT_TOKEN")

    @property
    def graph_authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.graph_tenant_id}"

    @property
    def graph_scope_list(self) -> list[str]:
        return [scope.strip() for scope in self.graph_scopes.split(",") if scope.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
