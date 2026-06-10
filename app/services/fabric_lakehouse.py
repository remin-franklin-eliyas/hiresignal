import asyncio
import json
import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class FabricLakehouseAdapter:
    """HTTP-backed Fabric Lakehouse adapter with basic retries and
    idempotency support. This improves reliability for demo/proof-of-
    concept deployments; production should use native SDKs and secure
    ingestion pipelines.
    """

    def __init__(self, settings: Settings, max_retries: int = 3, timeout: int = 15) -> None:
        self._settings = settings
        self._max_retries = max_retries
        self._timeout = timeout

    async def write_audit_record(self, record: dict[str, Any]) -> None:
        endpoint = self._settings.fabric_audit_endpoint
        token = self._settings.fabric_audit_token
        if not endpoint:
            raise RuntimeError("Fabric audit endpoint is not configured")
        if token is None:
            raise RuntimeError("Fabric audit token is not configured")

        # Compose idempotency key from candidate_hash + created_at when available
        idempotency_key = None
        try:
            if isinstance(record, dict):
                candidate = record.get("candidate_hash")
                created = record.get("created_at")
                if candidate and created:
                    idempotency_key = f"{candidate}:{created}"
        except Exception:
            idempotency_key = None

        headers = {
            "Authorization": f"Bearer {token.get_secret_value()}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        body = record if isinstance(record, dict) else json.loads(record)

        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(endpoint, headers=headers, json=body)
                    resp.raise_for_status()
                    return
            except Exception as exc:  # pragma: no cover - network behavior
                backoff = min(2 ** attempt, 10)
                logger.warning("Fabric lakehouse write failed (attempt %s): %s", attempt, exc)
                if attempt < self._max_retries:
                    await asyncio.sleep(backoff)
                    continue
                raise
