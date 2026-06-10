import asyncio
import logging
from collections.abc import Iterable

import httpx

from app.core.config import Settings, get_settings
from app.services.graph_client import GraphClient, get_graph_client

logger = logging.getLogger(__name__)


class TeamsPostingError(RuntimeError):
    pass


class TeamsClient:
    def __init__(self, settings: Settings, graph_client: GraphClient | None = None) -> None:
        self._settings = settings
        self._graph_client = graph_client or get_graph_client()

    async def post_shortlist(
        self,
        job_id: str,
        rubric_version: str,
        candidates: Iterable[dict],
    ) -> None:
        """Post an Adaptive Card shortlist to the configured Teams channel.

        Includes per-candidate summary and an action button to request
        a reasoning breakdown (`/teams/explain`). Retries on transient
        errors with exponential backoff.
        """
        channel = self._settings.teams_channel_id
        if not channel:
            return

        if "/" not in channel:
            raise TeamsPostingError("TEAMS_CHANNEL_ID must be in the form 'teamId/channelId'.")

        team_id, channel_id = channel.split("/", 1)

        # Build Adaptive Card body with per-candidate sections
        candidate_items = []
        for idx, c in enumerate(candidates, start=1):
            candidate_hash = c.get("candidate_hash", "unknown")
            short_hash = candidate_hash[:8] + ".." if len(candidate_hash) > 10 else candidate_hash
            overall = c.get("overall_score", "—")

            # Summarize reasoning fields if present
            skills = c.get("skills_match", {})
            exp = c.get("experience_relevance", {})
            role = c.get("role_fit", {})

            reasoning_text = (
                f"Skills: {skills.get('score', '—')} — {skills.get('reasoning', '')}\n"
                f"Experience: {exp.get('score', '—')} — {exp.get('reasoning', '')}\n"
                f"Role fit: {role.get('score', '—')} — {role.get('reasoning', '')}"
            )

            candidate_items.append(
                {
                    "type": "Container",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": f"{idx}. {short_hash} — {overall}",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": reasoning_text,
                            "wrap": True,
                            "spacing": "None",
                        },
                        {
                            "type": "ActionSet",
                            "actions": [
                                {
                                    "type": "Action.OpenUrl",
                                    "title": "Explain",
                                    "url": (
                                        f"/teams/explain?jobId={job_id}"
                                        f"&candidateHash={candidate_hash}"
                                    ),
                                },
                                {
                                    "type": "Action.OpenUrl",
                                    "title": "Request Review",
                                    "url": "https://example.com/manual-review",
                                },
                            ],
                        },
                    ],
                }
            )

        adaptive_card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Medium",
                                "weight": "Bolder",
                                "text": f"Shortlist for {job_id} (rubric {rubric_version})",
                            },
                            *candidate_items,
                        ],
                    },
                }
            ],
        }

        message_body = adaptive_card

        path = f"/teams/{team_id}/channels/{channel_id}/messages"
        url = f"{self._settings.graph_base_url.rstrip('/')}/{path.lstrip('/')}"

        token = self._graph_client._graph_auth.acquire_app_token()

        # Retry with exponential backoff for transient failures
        for attempt in range(1, 4):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(
                        url,
                        headers={
                            "Authorization": f"{token.token_type} {token.access_token}",
                            "Content-Type": "application/json",
                        },
                        json=message_body,
                    )
                    response.raise_for_status()
                    return
            except Exception as exc:  # pragma: no cover - network behavior
                backoff = min(2 ** attempt, 10)
                logger.warning("Teams post failed (attempt %s): %s", attempt, exc)
                if attempt < 3:
                    await asyncio.sleep(backoff)
                    continue
                raise TeamsPostingError("Failed to post shortlist to Teams after retries.") from exc


def get_teams_client() -> TeamsClient:
    return TeamsClient(get_settings())
