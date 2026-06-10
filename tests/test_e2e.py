import base64
from types import SimpleNamespace

import fitz
import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.models.attachments import GraphFileAttachment
from app.models.notifications import ChangeNotification
from app.models.scoring import CandidateScore, CriterionScore
from app.pipeline.ingestion import OutlookIngestionService
from app.services.audit_repository import SQLiteAuditRepository
from app.services.manual_review import ManualReviewQueue
from app.services.teams_client import TeamsClient


def build_settings(**overrides) -> Settings:
    params = {
        "GRAPH_TENANT_ID": "tenant-id",
        "GRAPH_CLIENT_ID": "client-id",
        "GRAPH_CLIENT_SECRET": "secret",
        "GRAPH_WEBHOOK_CLIENT_STATE": "client-state",
        "GRAPH_MONITORED_USER_ID": "recruiter@example.com",
        "GRAPH_BASE_URL": "https://graph.microsoft.com/v1.0",
    }
    # allow passing lowercase names; map them to env-style aliases
    params.update({k.upper(): v for k, v in overrides.items()})
    return Settings(**params)


def build_pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def build_attachment(name: str) -> GraphFileAttachment:
    content = build_pdf_bytes("E2E PDF content")
    return GraphFileAttachment.model_validate(
        {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "id": "attachment-1",
            "name": name,
            "size": len(content),
            "isInline": False,
            "contentBytes": base64.b64encode(content).decode("ascii"),
        }
    )


def build_notification(client_state: str = "client-state") -> ChangeNotification:
    return ChangeNotification.model_validate(
        {
            "subscriptionId": "sub-1",
            "clientState": client_state,
            "changeType": "created",
            "resource": "users/recruiter@example.com/messages/message-1",
            "resourceData": {"@odata.type": "#Microsoft.Graph.Message", "id": "message-1"},
        }
    )


class StubGraphAuth:
    def acquire_app_token(self):
        return SimpleNamespace(token_type="Bearer", access_token="token")


class StubGraphClient:
    def __init__(self):
        self._graph_auth = StubGraphAuth()


@pytest.mark.asyncio
async def test_teams_posting_uses_graph_and_http(monkeypatch, tmp_path):
    settings = build_settings(teams_channel_id="team1/channel1")
    graph_client = StubGraphClient()
    client = TeamsClient(settings, graph_client=graph_client)

    posted = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            posted['url'] = url
            posted['headers'] = headers
            posted['json'] = json
            return FakeResponse()

    monkeypatch.setattr(httpx, 'AsyncClient', FakeAsyncClient)

    await client.post_shortlist('job-1', 'v1', [{'candidate_hash': 'a'*64, 'overall_score': 88}])

    assert 'url' in posted
    assert settings.graph_base_url in posted['url']
    assert 'Authorization' in posted['headers']


@pytest.mark.asyncio
async def test_audit_persistence_integration(tmp_path):
    db_path = tmp_path / "audit.db"
    db_url = f"sqlite:///{db_path}"
    repo = SQLiteAuditRepository(db_url)

    # Build a minimal CandidateScoreAuditRecord via the scoring model
    record = {
        'candidate_hash': 'a'*64,
        'source_event_hash': 'e'*64,
        'job_id': 'job-1',
        'rubric_version': 'v1',
        'pipeline_version': 'p1',
        'overall_score': 90,
        'skills_match': {'criterion': 'skills_match', 'score': 90, 'reasoning': 'ok'},
        'experience_relevance': {
            'criterion': 'experience_relevance',
            'score': 80,
            'reasoning': 'ok',
        },
        'role_fit': {'criterion': 'role_fit', 'score': 70, 'reasoning': 'ok'},
        'manual_review_required': False,
        'created_at': '2026-01-01T00:00:00',
    }

    # Save using repo.save and read back
    # repo.save expects a CandidateScoreAuditRecord Pydantic instance, but the SQLiteRepo
    # accepts whatever model dumps to JSON when saved; use the model directly via import
    from app.models.audit import CandidateScoreAuditRecord

    model = CandidateScoreAuditRecord.model_validate(record)
    await repo.save(model)

    results = await repo.list_by_job('job-1')
    assert len(results) == 1
    assert results[0].candidate_hash == 'a'*64


@pytest.mark.asyncio
async def test_ingestion_end_to_end_writes_to_sqlite(tmp_path):
    # Use real SQLite repo for persistence
    db_path = tmp_path / "ingest.db"
    db_url = f"sqlite:///{db_path}"
    settings = build_settings(database_url=db_url)

    # Stub Graph client to return a single PDF attachment
    class StubGraphClient2:
        async def list_message_attachments(self, user_id: str, message_id: str):
            return [build_attachment('candidate.pdf')]

    # Simple scoring service that returns a CandidateScore
    class SimpleScoringService:
        async def score_document(self, document, rubric, candidate_identifier):
            return CandidateScore(
                candidate_hash='b'*64,
                job_id=rubric.job_id,
                rubric_version=rubric.version,
                skills_match=CriterionScore(
                    criterion='skills_match', score=90, reasoning='ok'
                ),
                experience_relevance=CriterionScore(
                    criterion='experience_relevance', score=80, reasoning='ok'
                ),
                role_fit=CriterionScore(criterion='role_fit', score=70, reasoning='ok'),
                overall_score=80,
            )

    review_queue = ManualReviewQueue()
    audit_repo = SQLiteAuditRepository(db_url)

    service = OutlookIngestionService(
        settings,
        StubGraphClient2(),
        review_queue,
        candidate_scoring_service=SimpleScoringService(),
        audit_repository=audit_repo,
    )

    result = await service.process_notification(build_notification())
    assert result.status in ('queued',)

    # The sample rubric in config/job_rubric.sample.json uses this job id
    records = await audit_repo.list_by_job('backend-ai-engineer-2026-06')
    assert len(records) == 1


def test_health_endpoint():
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json() == {'status': 'ok'}
