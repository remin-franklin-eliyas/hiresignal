import json
from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.models.rubric import RubricCriterion
from app.models.scoring import CriterionScore


class FoundryScoringError(RuntimeError):
    pass


class FoundryScoringClient:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client

    async def score_criterion(
        self,
        criterion: RubricCriterion,
        cv_text: str,
        job_title: str,
    ) -> CriterionScore:
        if not self._settings.azure_ai_foundry_endpoint:
            raise FoundryScoringError("Azure AI Foundry endpoint is not configured.")
        if self._settings.azure_ai_foundry_api_key is None:
            raise FoundryScoringError("Azure AI Foundry API key is not configured.")

        payload = self._build_payload(criterion, cv_text, job_title)
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=30)
        try:
            response = await client.post(
                self._settings.azure_ai_foundry_endpoint,
                headers={
                    "api-key": self._settings.azure_ai_foundry_api_key.get_secret_value(),
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return self._parse_response(response.json())
        except (httpx.HTTPError, ValidationError, KeyError, json.JSONDecodeError) as exc:
            raise FoundryScoringError("Azure AI Foundry scoring failed.") from exc
        finally:
            if owns_client:
                await client.aclose()

    def _build_payload(
        self,
        criterion: RubricCriterion,
        cv_text: str,
        job_title: str,
    ) -> dict[str, Any]:
        return {
            "model": self._settings.azure_ai_foundry_model,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "criterion_score",
                    "schema": CriterionScore.model_json_schema(),
                    "strict": True,
                },
            },
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are HireSignal's enterprise recruiting scoring component. "
                        "Return only schema-valid JSON. Do not include raw PII in reasoning."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Job title: {job_title}\n"
                        f"Criterion: {criterion.name}\n"
                        f"Required signals: {', '.join(criterion.required_signals)}\n"
                        "Score the CV text from 0 to 100 for this criterion. "
                        "Reason concisely and cite only capability signals, not personal data.\n\n"
                        f"CV text:\n{cv_text}"
                    ),
                },
            ],
        }

    @staticmethod
    def _parse_response(payload: Mapping[str, Any]) -> CriterionScore:
        if "choices" in payload:
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content) if isinstance(content, str) else content
            return CriterionScore.model_validate(parsed)
        return CriterionScore.model_validate(payload)

