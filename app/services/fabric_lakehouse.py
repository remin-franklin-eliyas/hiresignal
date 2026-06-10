from typing import Any

import httpx

from app.core.config import Settings


class FabricLakehouseAdapter:
    """Minimal Fabric Lakehouse adapter that posts audit records to a
    configured HTTP endpoint. Production deployments should replace this
    with a proper Lakehouse writer using authenticated SDKs or secure
    ingestion endpoints.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def write_audit_record(self, record: dict[str, Any]) -> None:
        endpoint = self._settings.fabric_audit_endpoint
        token = self._settings.fabric_audit_token
        if not endpoint:
            raise RuntimeError("Fabric audit endpoint is not configured")
        if token is None:
            raise RuntimeError("Fabric audit token is not configured")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {token.get_secret_value()}",
                    "Content-Type": "application/json",
                },
                json=record,
            )
            resp.raise_for_status()
