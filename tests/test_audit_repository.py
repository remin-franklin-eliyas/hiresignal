import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.models.audit import CandidateScoreAuditRecord
from app.models.scoring import CandidateScore, CriterionScore
from app.pipeline.privacy import hash_candidate_identifier
from app.services.audit_repository import (
    AuditPersistenceError,
    FabricAuditRepository,
    SQLiteAuditRepository,
)


def build_score() -> CandidateScore:
    return CandidateScore(
        candidate_hash=hash_candidate_identifier("message-1:candidate.pdf"),
        job_id="backend-ai-engineer-2026-06",
        rubric_version="2026.06.10",
        skills_match=CriterionScore(
            criterion="skills_match",
            score=90,
            reasoning="Strong Python and FastAPI evidence.",
            matched_signals=["Python", "FastAPI"],
            missing_signals=["Azure AI"],
        ),
        experience_relevance=CriterionScore(
            criterion="experience_relevance",
            score=70,
            reasoning="Production API experience is present.",
            matched_signals=["production APIs"],
            missing_signals=["cloud deployment"],
        ),
        role_fit=CriterionScore(
            criterion="role_fit",
            score=50,
            reasoning="Some communication evidence is present.",
            matched_signals=["communication"],
            missing_signals=["recruiting workflow empathy"],
        ),
        overall_score=74,
    )


def build_record() -> CandidateScoreAuditRecord:
    return CandidateScoreAuditRecord.from_candidate_score(
        score=build_score(),
        pipeline_version="2026.06.10",
        source_event_hash=hash_candidate_identifier("message-1"),
    )


def build_settings(endpoint: str | None = None) -> Settings:
    return Settings(
        GRAPH_TENANT_ID="tenant-id",
        GRAPH_CLIENT_ID="client-id",
        GRAPH_CLIENT_SECRET="secret",
        GRAPH_WEBHOOK_CLIENT_STATE="client-state",
        GRAPH_MONITORED_USER_ID="recruiter@example.com",
        FABRIC_AUDIT_ENDPOINT=endpoint,
        FABRIC_AUDIT_TOKEN="fabric-token" if endpoint else None,
    )


def test_audit_record_forbids_raw_cv_text() -> None:
    payload = build_record().model_dump()
    payload["cv_text"] = "raw CV text must not be stored"

    with pytest.raises(ValidationError):
        CandidateScoreAuditRecord.model_validate(payload)


async def test_sqlite_audit_repository_round_trips_score_without_pii(tmp_path) -> None:
    repository = SQLiteAuditRepository(f"sqlite:///{tmp_path / 'audit.sqlite3'}")
    record = build_record()

    await repository.save(record)
    records = await repository.list_by_job(record.job_id)

    assert len(records) == 1
    assert records[0].candidate_hash == record.candidate_hash
    assert records[0].overall_score == 74
    serialized = records[0].model_dump_json()
    assert "candidate.pdf" not in serialized
    assert "raw CV" not in serialized


async def test_fabric_audit_repository_posts_record_to_configured_endpoint() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://fabric.example/audit"
        assert request.headers["authorization"] == "Bearer fabric-token"
        assert "raw CV" not in request.content.decode()
        return httpx.Response(202)

    repository = FabricAuditRepository(
        settings=build_settings(endpoint="https://fabric.example/audit"),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    await repository.save(build_record())


async def test_fabric_audit_repository_requires_configuration() -> None:
    repository = FabricAuditRepository(settings=build_settings())

    with pytest.raises(AuditPersistenceError):
        await repository.save(build_record())

