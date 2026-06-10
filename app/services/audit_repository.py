from pathlib import Path
import json
import sqlite3
from typing import Protocol

import httpx

from app.core.config import Settings, get_settings
from app.models.audit import CandidateScoreAuditRecord


class AuditPersistenceError(RuntimeError):
    pass


class AuditRepository(Protocol):
    async def save(self, record: CandidateScoreAuditRecord) -> None:
        pass

    async def list_by_job(self, job_id: str) -> list[CandidateScoreAuditRecord]:
        pass


class SQLiteAuditRepository:
    def __init__(self, database_url: str) -> None:
        self._database_path = self._database_path_from_url(database_url)
        self._ensure_schema()

    async def save(self, record: CandidateScoreAuditRecord) -> None:
        try:
            with sqlite3.connect(self._database_path) as connection:
                connection.execute(
                    """
                    INSERT INTO candidate_score_audit (
                        candidate_hash,
                        source_event_hash,
                        job_id,
                        rubric_version,
                        pipeline_version,
                        overall_score,
                        skills_match_json,
                        experience_relevance_json,
                        role_fit_json,
                        manual_review_required,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.candidate_hash,
                        record.source_event_hash,
                        record.job_id,
                        record.rubric_version,
                        record.pipeline_version,
                        record.overall_score,
                        record.skills_match.model_dump_json(),
                        record.experience_relevance.model_dump_json(),
                        record.role_fit.model_dump_json(),
                        int(record.manual_review_required),
                        record.created_at.isoformat(),
                    ),
                )
        except sqlite3.Error as exc:
            raise AuditPersistenceError("Unable to persist candidate score audit record.") from exc

    async def list_by_job(self, job_id: str) -> list[CandidateScoreAuditRecord]:
        try:
            with sqlite3.connect(self._database_path) as connection:
                connection.row_factory = sqlite3.Row
                rows = connection.execute(
                    """
                    SELECT
                        candidate_hash,
                        source_event_hash,
                        job_id,
                        rubric_version,
                        pipeline_version,
                        overall_score,
                        skills_match_json,
                        experience_relevance_json,
                        role_fit_json,
                        manual_review_required,
                        created_at
                    FROM candidate_score_audit
                    WHERE job_id = ?
                    ORDER BY overall_score DESC, created_at ASC
                    """,
                    (job_id,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise AuditPersistenceError("Unable to read candidate score audit records.") from exc

        return [self._record_from_row(row) for row in rows]

    def _ensure_schema(self) -> None:
        try:
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self._database_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS candidate_score_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        candidate_hash TEXT NOT NULL,
                        source_event_hash TEXT,
                        job_id TEXT NOT NULL,
                        rubric_version TEXT NOT NULL,
                        pipeline_version TEXT NOT NULL,
                        overall_score INTEGER NOT NULL,
                        skills_match_json TEXT NOT NULL,
                        experience_relevance_json TEXT NOT NULL,
                        role_fit_json TEXT NOT NULL,
                        manual_review_required INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_candidate_score_audit_job_score
                    ON candidate_score_audit (job_id, overall_score DESC)
                    """
                )
        except sqlite3.Error as exc:
            raise AuditPersistenceError("Unable to initialize local audit store.") from exc

    @staticmethod
    def _database_path_from_url(database_url: str) -> Path:
        if not database_url.startswith("sqlite:///"):
            raise AuditPersistenceError("Only sqlite:/// URLs are supported by SQLiteAuditRepository.")
        return Path(database_url.removeprefix("sqlite:///"))

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> CandidateScoreAuditRecord:
        return CandidateScoreAuditRecord.model_validate(
            {
                "candidate_hash": row["candidate_hash"],
                "source_event_hash": row["source_event_hash"],
                "job_id": row["job_id"],
                "rubric_version": row["rubric_version"],
                "pipeline_version": row["pipeline_version"],
                "overall_score": row["overall_score"],
                "skills_match": json.loads(row["skills_match_json"]),
                "experience_relevance": json.loads(row["experience_relevance_json"]),
                "role_fit": json.loads(row["role_fit_json"]),
                "manual_review_required": bool(row["manual_review_required"]),
                "created_at": row["created_at"],
            }
        )


class FabricAuditRepository:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client

    async def save(self, record: CandidateScoreAuditRecord) -> None:
        if not self._settings.fabric_audit_endpoint:
            raise AuditPersistenceError("Fabric audit endpoint is not configured.")
        if self._settings.fabric_audit_token is None:
            raise AuditPersistenceError("Fabric audit token is not configured.")

        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=15)
        try:
            response = await client.post(
                self._settings.fabric_audit_endpoint,
                headers={
                    "Authorization": (
                        f"Bearer {self._settings.fabric_audit_token.get_secret_value()}"
                    ),
                    "Content-Type": "application/json",
                },
                json=record.model_dump(mode="json"),
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AuditPersistenceError("Unable to persist audit record to Fabric.") from exc
        finally:
            if owns_client:
                await client.aclose()

    async def list_by_job(self, job_id: str) -> list[CandidateScoreAuditRecord]:
        raise AuditPersistenceError(
            "Fabric audit reads are intentionally handled by downstream Fabric reporting."
        )


def get_audit_repository(settings: Settings | None = None) -> AuditRepository:
    resolved_settings = settings or get_settings()
    if resolved_settings.fabric_audit_mode.lower() == "fabric":
        return FabricAuditRepository(resolved_settings)
    return SQLiteAuditRepository(resolved_settings.database_url)
