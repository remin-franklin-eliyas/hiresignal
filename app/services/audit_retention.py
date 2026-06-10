"""Audit retention policy management for compliance."""

from datetime import UTC, datetime, timedelta
import logging

from app.core.config import Settings, get_settings
from app.services.audit_repository import SQLiteAuditRepository

logger = logging.getLogger(__name__)


class AuditRetentionPolicy:
    """Manages audit record retention and deletion based on configured policies."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        # Default retention: 90 days unless overridden
        self.retention_days = int(self.settings.__dict__.get('audit_retention_days', 90))

    async def cleanup_expired_records(self, database_url: str | None = None) -> int:
        """Delete audit records older than retention policy.

        Args:
            database_url: SQLite database URL. If None, uses settings.database_url.

        Returns:
            Number of records deleted.
        """
        db_url = database_url or self.settings.database_url
        if not db_url.startswith('sqlite:///'):
            logger.warning(
                "Audit retention cleanup only supported for SQLite. "
                "Fabric audit records are managed by downstream retention policies."
            )
            return 0

        repo = SQLiteAuditRepository(db_url)
        cutoff_date = datetime.now(UTC) - timedelta(days=self.retention_days)

        try:
            import sqlite3
            from pathlib import Path

            db_path = Path(db_url.removeprefix('sqlite:///'))
            with sqlite3.connect(db_path) as connection:
                cursor = connection.execute(
                    """
                    DELETE FROM candidate_score_audit
                    WHERE created_at < ?
                    """,
                    (cutoff_date.isoformat(),),
                )
                deleted_count = cursor.rowcount
                connection.commit()
                logger.info(
                    "Deleted %d audit records older than %d days (cutoff: %s)",
                    deleted_count,
                    self.retention_days,
                    cutoff_date.isoformat(),
                )
                return deleted_count
        except Exception as exc:
            logger.error("Audit cleanup failed: %s", exc)
            raise


def get_audit_retention_policy(settings: Settings | None = None) -> AuditRetentionPolicy:
    """Factory for audit retention policy."""
    return AuditRetentionPolicy(settings)
