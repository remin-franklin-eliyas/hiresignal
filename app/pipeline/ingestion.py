from typing import Literal

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.models.attachments import GraphFileAttachment
from app.models.audit import CandidateScoreAuditRecord
from app.models.documents import ExtractedDocument
from app.models.notifications import (
    ChangeNotification,
    ChangeNotificationCollection,
    ManualReviewItem,
)
from app.pipeline.attachments import (
    AttachmentValidationError,
    validate_attachment_type,
    virus_scan_stub,
)
from app.pipeline.extraction import (
    CvTextExtractor,
    DocumentExtractionError,
    get_cv_text_extractor,
)
from app.pipeline.rubric import RubricLoader, RubricLoadError, get_rubric_loader
from app.pipeline.scoring import (
    CandidateScoringError,
    CandidateScoringService,
    get_candidate_scoring_service,
)
from app.pipeline.privacy import hash_candidate_identifier
from app.services.audit_repository import (
    AuditPersistenceError,
    AuditRepository,
    get_audit_repository,
)
from app.services.graph_client import GraphClient, GraphClientError, get_graph_client
from app.services.manual_review import ManualReviewQueue, get_manual_review_queue


class IngestionResult(BaseModel):
    message_id: str | None
    status: Literal["queued", "manual_review"]
    reason: str | None = None
    accepted_attachments: int = 0
    extracted_documents: int = 0
    scored_candidates: int = 0
    audited_candidates: int = 0
    rubric_version: str | None = None


class OutlookIngestionService:
    def __init__(
        self,
        settings: Settings,
        graph_client: GraphClient,
        manual_review_queue: ManualReviewQueue,
        cv_text_extractor: CvTextExtractor | None = None,
        rubric_loader: RubricLoader | None = None,
        candidate_scoring_service: CandidateScoringService | None = None,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self._settings = settings
        self._graph_client = graph_client
        self._manual_review_queue = manual_review_queue
        self._cv_text_extractor = cv_text_extractor or get_cv_text_extractor()
        self._rubric_loader = rubric_loader or get_rubric_loader(settings)
        self._candidate_scoring_service = (
            candidate_scoring_service or get_candidate_scoring_service()
        )
        self._audit_repository = audit_repository or get_audit_repository(settings)

    async def process_notifications(
        self,
        notifications: ChangeNotificationCollection,
    ) -> list[IngestionResult]:
        results: list[IngestionResult] = []
        for notification in notifications.value:
            results.append(await self.process_notification(notification))
        return results

    async def process_notification(self, notification: ChangeNotification) -> IngestionResult:
        message_id = notification.message_id
        if not self._is_trusted_notification(notification):
            return self._queue_manual_review(notification, "client_state_mismatch")

        if message_id is None:
            return self._queue_manual_review(notification, "missing_message_id")

        try:
            attachments = await self._graph_client.list_message_attachments(
                user_id=self._settings.graph_monitored_user_id,
                message_id=message_id,
            )
        except GraphClientError:
            return self._queue_manual_review(notification, "graph_attachment_fetch_failed")

        try:
            rubric = self._rubric_loader.load()
        except RubricLoadError:
            return self._queue_manual_review(notification, "rubric_load_failed")

        extracted_documents = self._extract_supported_attachments(notification, attachments)
        if not extracted_documents:
            return self._queue_manual_review(notification, "no_supported_cv_attachment")

        scored_count = 0
        audited_count = 0
        for document in extracted_documents:
            try:
                score = await self._candidate_scoring_service.score_document(
                    document=document,
                    rubric=rubric,
                    candidate_identifier=f"{message_id}:{document.filename}",
                )
            except CandidateScoringError:
                self._queue_manual_review(
                    notification,
                    "candidate_scoring_failed",
                    attachment_name=document.filename,
                )
                continue
            scored_count += 1

            try:
                await self._audit_repository.save(
                    CandidateScoreAuditRecord.from_candidate_score(
                        score=score,
                        pipeline_version=self._settings.pipeline_version,
                        source_event_hash=hash_candidate_identifier(message_id),
                    )
                )
            except AuditPersistenceError:
                self._queue_manual_review(
                    notification,
                    "audit_persistence_failed",
                    attachment_name=document.filename,
                )
                continue
            audited_count += 1

        if scored_count == 0:
            return self._queue_manual_review(notification, "no_scored_candidates")
        if audited_count == 0:
            return self._queue_manual_review(notification, "no_audited_candidates")

        return IngestionResult(
            message_id=message_id,
            status="queued",
            accepted_attachments=len(extracted_documents),
            extracted_documents=len(extracted_documents),
            scored_candidates=scored_count,
            audited_candidates=audited_count,
            rubric_version=rubric.version,
        )

    def _is_trusted_notification(self, notification: ChangeNotification) -> bool:
        expected = self._settings.graph_webhook_client_state.get_secret_value()
        return notification.client_state == expected

    def _extract_supported_attachments(
        self,
        notification: ChangeNotification,
        attachments: list[GraphFileAttachment],
    ) -> list[ExtractedDocument]:
        extracted_documents: list[ExtractedDocument] = []
        for attachment in attachments:
            if attachment.is_inline:
                continue
            try:
                validate_attachment_type(attachment.name)
                content = attachment.decoded_content()
                if not content or not virus_scan_stub(content):
                    self._queue_manual_review(
                        notification,
                        "attachment_scan_failed",
                        attachment_name=attachment.name,
                    )
                    continue
                extracted_document = self._cv_text_extractor.extract(attachment.name, content)
            except (AttachmentValidationError, ValueError):
                self._queue_manual_review(
                    notification,
                    "unsupported_attachment_type",
                    attachment_name=attachment.name,
                )
                continue
            except DocumentExtractionError:
                self._queue_manual_review(
                    notification,
                    "cv_text_extraction_failed",
                    attachment_name=attachment.name,
                )
                continue
            extracted_documents.append(extracted_document)
        return extracted_documents

    def _queue_manual_review(
        self,
        notification: ChangeNotification,
        reason: str,
        attachment_name: str | None = None,
    ) -> IngestionResult:
        item = ManualReviewItem(
            reason=reason,
            message_id=notification.message_id,
            attachment_name=attachment_name,
            subscription_id=notification.subscription_id,
        )
        self._manual_review_queue.enqueue(item)
        return IngestionResult(
            message_id=notification.message_id,
            status="manual_review",
            reason=reason,
        )


def get_outlook_ingestion_service() -> OutlookIngestionService:
    return OutlookIngestionService(
        settings=get_settings(),
        graph_client=get_graph_client(),
        manual_review_queue=get_manual_review_queue(),
        cv_text_extractor=get_cv_text_extractor(),
        rubric_loader=get_rubric_loader(),
        candidate_scoring_service=get_candidate_scoring_service(),
        audit_repository=get_audit_repository(),
    )
