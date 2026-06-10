import base64

import fitz

from app.core.config import Settings
from app.models.attachments import GraphFileAttachment
from app.models.notifications import ChangeNotification, ChangeNotificationCollection
from app.models.scoring import CandidateScore, CriterionScore
from app.pipeline.ingestion import OutlookIngestionService
from app.pipeline.scoring import CandidateScoringError
from app.services.audit_repository import AuditPersistenceError
from app.services.manual_review import ManualReviewQueue


class StubGraphClient:
    def __init__(self, attachments: list[GraphFileAttachment]) -> None:
        self.attachments = attachments

    async def list_message_attachments(
        self,
        user_id: str,
        message_id: str,
    ) -> list[GraphFileAttachment]:
        assert user_id == "recruiter@example.com"
        assert message_id == "message-1"
        return self.attachments


class StubScoringService:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.scored_documents = 0

    async def score_document(self, document, rubric, candidate_identifier):
        if self.should_fail:
            raise CandidateScoringError("boom")
        self.scored_documents += 1
        return CandidateScore(
            candidate_hash="a" * 64,
            job_id=rubric.job_id,
            rubric_version=rubric.version,
            skills_match=CriterionScore(
                criterion="skills_match",
                score=90,
                reasoning="Strong skills match.",
            ),
            experience_relevance=CriterionScore(
                criterion="experience_relevance",
                score=80,
                reasoning="Relevant experience.",
            ),
            role_fit=CriterionScore(
                criterion="role_fit",
                score=70,
                reasoning="Good role fit.",
            ),
            overall_score=82,
        )


class StubAuditRepository:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.saved_records = []

    async def save(self, record) -> None:
        if self.should_fail:
            raise AuditPersistenceError("boom")
        self.saved_records.append(record)

    async def list_by_job(self, job_id: str):
        return [record for record in self.saved_records if record.job_id == job_id]


def build_settings() -> Settings:
    return Settings(
        GRAPH_TENANT_ID="tenant-id",
        GRAPH_CLIENT_ID="client-id",
        GRAPH_CLIENT_SECRET="secret",
        GRAPH_WEBHOOK_CLIENT_STATE="client-state",
        GRAPH_MONITORED_USER_ID="recruiter@example.com",
    )


def build_notification(client_state: str = "client-state") -> ChangeNotification:
    return ChangeNotification.model_validate(
        {
            "subscriptionId": "sub-1",
            "clientState": client_state,
            "changeType": "created",
            "resource": "users/recruiter@example.com/messages/message-1",
            "resourceData": {
                "@odata.type": "#Microsoft.Graph.Message",
                "id": "message-1",
            },
        }
    )


def build_attachment(name: str) -> GraphFileAttachment:
    content = build_pdf_bytes("Python FastAPI Azure AI")
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


def build_pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


async def test_ingestion_queues_supported_cv_attachment() -> None:
    review_queue = ManualReviewQueue()
    scoring_service = StubScoringService()
    audit_repository = StubAuditRepository()
    service = OutlookIngestionService(
        build_settings(),
        StubGraphClient([build_attachment("candidate.pdf")]),
        review_queue,
        candidate_scoring_service=scoring_service,
        audit_repository=audit_repository,
    )

    results = await service.process_notifications(
        ChangeNotificationCollection(value=[build_notification()])
    )

    assert results[0].status == "queued"
    assert results[0].accepted_attachments == 1
    assert results[0].scored_candidates == 1
    assert results[0].audited_candidates == 1
    assert scoring_service.scored_documents == 1
    assert len(audit_repository.saved_records) == 1
    assert review_queue.list_items() == []


async def test_ingestion_manual_review_on_client_state_mismatch() -> None:
    review_queue = ManualReviewQueue()
    service = OutlookIngestionService(
        build_settings(),
        StubGraphClient([build_attachment("candidate.pdf")]),
        review_queue,
        candidate_scoring_service=StubScoringService(),
        audit_repository=StubAuditRepository(),
    )

    result = await service.process_notification(build_notification(client_state="wrong"))

    assert result.status == "manual_review"
    assert result.reason == "client_state_mismatch"
    assert review_queue.list_items()[0].reason == "client_state_mismatch"


async def test_ingestion_manual_review_on_unsupported_attachment() -> None:
    review_queue = ManualReviewQueue()
    service = OutlookIngestionService(
        build_settings(),
        StubGraphClient([build_attachment("candidate.txt")]),
        review_queue,
        candidate_scoring_service=StubScoringService(),
        audit_repository=StubAuditRepository(),
    )

    result = await service.process_notification(build_notification())

    assert result.status == "manual_review"
    assert result.reason == "no_supported_cv_attachment"
    reasons = [item.reason for item in review_queue.list_items()]
    assert "unsupported_attachment_type" in reasons
    assert "no_supported_cv_attachment" in reasons


async def test_ingestion_manual_review_when_scoring_fails() -> None:
    review_queue = ManualReviewQueue()
    service = OutlookIngestionService(
        build_settings(),
        StubGraphClient([build_attachment("candidate.pdf")]),
        review_queue,
        candidate_scoring_service=StubScoringService(should_fail=True),
        audit_repository=StubAuditRepository(),
    )

    result = await service.process_notification(build_notification())

    assert result.status == "manual_review"
    assert result.reason == "no_scored_candidates"
    reasons = [item.reason for item in review_queue.list_items()]
    assert "candidate_scoring_failed" in reasons
    assert "no_scored_candidates" in reasons


async def test_ingestion_manual_review_when_audit_persistence_fails() -> None:
    review_queue = ManualReviewQueue()
    service = OutlookIngestionService(
        build_settings(),
        StubGraphClient([build_attachment("candidate.pdf")]),
        review_queue,
        candidate_scoring_service=StubScoringService(),
        audit_repository=StubAuditRepository(should_fail=True),
    )

    result = await service.process_notification(build_notification())

    assert result.status == "manual_review"
    assert result.reason == "no_audited_candidates"
    reasons = [item.reason for item in review_queue.list_items()]
    assert "audit_persistence_failed" in reasons
    assert "no_audited_candidates" in reasons
