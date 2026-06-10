from fastapi.testclient import TestClient

from app.main import app
from app.services.audit_repository import get_audit_repository
from app.models.audit import CandidateScoreAuditRecord


def test_teams_explain_not_found(monkeypatch):
    client = TestClient(app)

    # Ensure the audit repository returns no records for the job
    class DummyRepo:
        async def list_by_job(self, job_id: str):
            return []

    app.dependency_overrides[get_audit_repository] = lambda: DummyRepo()

    resp = client.get("/teams/explain", params={"jobId": "job-x", "candidateHash": "deadbeef"})
    assert resp.status_code == 404


def test_teams_explain_returns_record(monkeypatch):
    client = TestClient(app)

    record = CandidateScoreAuditRecord.model_validate(
        {
            "candidate_hash": "a" * 64,
            "source_event_hash": None,
            "job_id": "job-x",
            "rubric_version": "1",
            "pipeline_version": "pv",
            "overall_score": 90,
            "skills_match": {"criterion": "skills_match", "score": 90, "reasoning": "ok", "matched_signals": [], "missing_signals": []},
            "experience_relevance": {"criterion": "experience_relevance", "score": 90, "reasoning": "ok", "matched_signals": [], "missing_signals": []},
            "role_fit": {"criterion": "role_fit", "score": 90, "reasoning": "ok", "matched_signals": [], "missing_signals": []},
            "manual_review_required": False,
            "created_at": "2026-06-10T00:00:00Z",
        }
    )

    class DummyRepo:
        async def list_by_job(self, job_id: str):
            return [record]

    app.dependency_overrides[get_audit_repository] = lambda: DummyRepo()

    resp = client.get("/teams/explain", params={"jobId": "job-x", "candidateHash": "" + "a" * 64})
    assert resp.status_code == 200
    assert resp.json()["candidate_hash"] == "a" * 64
