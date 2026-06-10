#!/usr/bin/env python
"""Management CLI for HireSignal operational tasks.

Usage:
  python -m app.cli audit cleanup [--database-url=<url>]
"""

import asyncio
import logging
import sys
from argparse import ArgumentParser

from app.core.config import get_settings
from app.services.audit_retention import get_audit_retention_policy

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure basic logging for CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


async def audit_cleanup(database_url: str | None = None) -> None:
    """Clean up expired audit records based on retention policy."""
    settings = get_settings()
    policy = get_audit_retention_policy(settings)
    deleted = await policy.cleanup_expired_records(database_url)
    print(f"Cleanup complete: {deleted} records deleted.")


def main() -> int:
    """Parse CLI arguments and execute commands."""
    setup_logging()
    parser = ArgumentParser(description="HireSignal management CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Audit subcommand
    audit_parser = subparsers.add_parser("audit", help="Audit management commands")
    audit_subparsers = audit_parser.add_subparsers(dest="audit_command")

    cleanup_parser = audit_subparsers.add_parser("cleanup", help="Clean up expired audit records")
    cleanup_parser.add_argument(
        "--database-url",
        default=None,
        help="SQLite database URL (defaults to configured DATABASE_URL)",
    )

    args = parser.parse_args()

    if args.command == "audit" and args.audit_command == "cleanup":
        asyncio.run(audit_cleanup(args.database_url))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
