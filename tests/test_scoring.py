import httpx
import pytest

from app.core.config import Settings
from app.models.documents import DocumentType, ExtractedDocument
from app.models.rubric import JobRubric
from app.pipeline.scoring import CandidateScoringError, CandidateScoringService
from app.services.foundry_scoring import FoundryScoringClient, FoundryScoringError


def build_settings(
    *,
    endpoint: str | None = None,
    fallback: bool = True,
) -> Settings:
    return Settings(
        GRAPH_TENANT_ID="tenant-id",
        GRAPH_CLIENT_ID="client-id",
        GRAPH_CLIENT_SECRET="secret",
        GRAPH_WEBHOOK_CLIENT_STATE="client-state",
        GRAPH_MONITORED_USER_ID="recruiter@example.com",
        AZURE_AI_FOUNDRY_ENDPOINT=endpoint,
        AZURE_AI_FOUNDRY_API_KEY="foundry-key" if endpoint else None,
        USE_LOCAL_SCORING_FALLBACK=fallback,
    )


def build_rubric() -> JobRubric:
    return JobRubric.model_validate(
        {
            "job_id": "backend-ai-engineer-2026-06",
            "version": "2026.06.10",
            "title": "Backend AI Engineer",
            "criteria": [
                {
                    "name": "skills_match",
                    "weight": 0.4,
                    "required_signals": ["Python", "FastAPI", "Azure AI"],
                },
                {
                    "name": "experience_relevance",
                    "weight": 0.35,
                    "required_signals": ["production APIs", "cloud deployment"],
                },
                {
                    "name": "role_fit",
                    "weight": 0.25,
                    "required_signals": ["communication", "recruiting workflow empathy"],
                },
            ],
        }
    )


def build_document(text: str) -> ExtractedDocument:
    return ExtractedDocument.from_text("candidate.pdf", DocumentType.PDF, text)


async def test_local_fallback_scores_candidate_with_weighted_overall() -> None:
    service = CandidateScoringService(settings=build_settings())

    score = await service.score_document(
        document=build_document("Python FastAPI production APIs communication"),
        rubric=build_rubric(),
        candidate_identifier="message-1:candidate.pdf",
    )

    assert score.job_id == "backend-ai-engineer-2026-06"
    assert score.rubric_version == "2026.06.10"
    assert score.skills_match.score == 67
    assert score.experience_relevance.score == 50
    assert score.role_fit.score == 50
    assert score.overall_score == 57
    assert len(score.candidate_hash) == 64


async def test_scoring_raises_when_foundry_fails_and_fallback_disabled() -> None:
    service = CandidateScoringService(settings=build_settings(fallback=False))

    with pytest.raises(CandidateScoringError):
        await service.score_document(
            document=build_document("Python"),
            rubric=build_rubric(),
            candidate_identifier="message-1:candidate.pdf",
        )


async def test_foundry_client_parses_schema_bound_chat_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read()
        assert b"response_format" in payload
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"criterion":"skills_match","score":88,'
                                '"reasoning":"Strong signal match.",'
                                '"matched_signals":["Python"],"missing_signals":[]}'
                            )
                        }
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    foundry_client = FoundryScoringClient(
        settings=build_settings(endpoint="https://foundry.example/score"),
        http_client=client,
    )

    score = await foundry_client.score_criterion(
        criterion=build_rubric().criteria[0],
        cv_text="Python",
        job_title="Backend AI Engineer",
    )

    assert score.criterion == "skills_match"
    assert score.score == 88


async def test_foundry_client_rejects_invalid_schema_response() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    foundry_client = FoundryScoringClient(
        settings=build_settings(endpoint="https://foundry.example/score"),
        http_client=client,
    )

    with pytest.raises(FoundryScoringError):
        await foundry_client.score_criterion(
            criterion=build_rubric().criteria[0],
            cv_text="Python",
            job_title="Backend AI Engineer",
        )

