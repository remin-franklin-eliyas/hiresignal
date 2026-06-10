from typing import Iterable

from app.core.config import Settings, get_settings
from app.services.graph_client import GraphClient, get_graph_client


class TeamsPostingError(RuntimeError):
    pass


class TeamsClient:
    def __init__(self, settings: Settings, graph_client: GraphClient | None = None) -> None:
        self._settings = settings
        self._graph_client = graph_client or get_graph_client()

    async def post_shortlist(self, job_id: str, rubric_version: str, candidates: Iterable[dict]) -> None:
        """Post a simple plaintext shortlist to the configured Teams channel.

        `TEAMS_CHANNEL_ID` is expected in the form "{team_id}/{channel_id}".
        If not configured, this method is a no-op.
        """
        channel = self._settings.teams_channel_id
        if not channel:
            return

        if "/" not in channel:
            raise TeamsPostingError("TEAMS_CHANNEL_ID must be in the form 'teamId/channelId'.")

        team_id, channel_id = channel.split("/", 1)

        lines = [f"Shortlist for job {job_id} (rubric {rubric_version}):"]
        for idx, c in enumerate(candidates, start=1):
            lines.append(f"{idx}. {c.get('candidate_hash')} — {c.get('overall_score')}")

        # Build a minimal Adaptive Card payload for a prettier Teams message.
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
                            {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": f"Shortlist for {job_id} (rubric {rubric_version})"},
                            {"type": "TextBlock", "text": "\n".join(lines[1:]), "wrap": True},
                        ],
                    },
                }
            ],
        }

        message_body = adaptive_card

        path = f"/teams/{team_id}/channels/{channel_id}/messages"
        url = f"{self._settings.graph_base_url.rstrip('/')}/{path.lstrip('/')}"

        token = self._graph_client._graph_auth.acquire_app_token()
        import httpx

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
        except Exception as exc:
            raise TeamsPostingError("Failed to post shortlist to Teams.") from exc


def get_teams_client() -> TeamsClient:
    return TeamsClient(get_settings())
