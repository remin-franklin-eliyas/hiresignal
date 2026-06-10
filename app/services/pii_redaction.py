"""PII and sensitive data redaction utilities for logging and output."""

import logging
import re
from re import Pattern


class SensitivePatterns:
    """Patterns for detecting and redacting sensitive information."""

    # Email addresses (non-exhaustive but catches common patterns)
    EMAIL: Pattern = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    # Phone numbers (US format and variations)
    PHONE: Pattern = re.compile(
        r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
    )

    # Social Security Numbers
    SSN: Pattern = re.compile(
        r'\b(?!000|666|9\d{2})\d{3}[-]?(?!00)\d{2}[-]?(?!0000)\d{4}\b'
    )

    # Credit card numbers (simplified)
    CREDIT_CARD: Pattern = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')

    # API keys and tokens (common patterns)
    API_KEY: Pattern = re.compile(
        r'(?:api[_-]?key|token|secret|password)\s*[=:]\s*([^\s,;]+)',
        re.IGNORECASE,
    )

    # Bearer tokens
    BEARER_TOKEN: Pattern = re.compile(
        r'Bearer\s+([A-Za-z0-9\-._~+/]+=*)', re.IGNORECASE
    )


class RedactionFilter(logging.Filter):
    """Logging filter that redacts sensitive information from log records."""

    def __init__(self, name: str = '', redact_patterns: list[Pattern] | None = None) -> None:
        super().__init__(name)
        self.redact_patterns = redact_patterns or [
            SensitivePatterns.EMAIL,
            SensitivePatterns.PHONE,
            SensitivePatterns.SSN,
            SensitivePatterns.CREDIT_CARD,
            SensitivePatterns.API_KEY,
            SensitivePatterns.BEARER_TOKEN,
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive info from log record message and args."""
        record.msg = self._redact_string(str(record.msg))

        # Redact args if they're a dict or tuple
        if isinstance(record.args, dict):
            record.args = {k: self._redact_string(str(v)) for k, v in record.args.items()}
        elif isinstance(record.args, (tuple, list)):
            record.args = tuple(self._redact_string(str(arg)) for arg in record.args)
        elif record.args:
            record.args = (self._redact_string(str(record.args)),)

        return True

    def _redact_string(self, text: str) -> str:
        """Apply all redaction patterns to a string."""
        for pattern in self.redact_patterns:
            text = pattern.sub('[REDACTED]', text)
        return text


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging with PII redaction filter.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Create console handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Add redaction filter to all handlers
    redaction_filter = RedactionFilter()
    console_handler.addFilter(redaction_filter)

    # Format: timestamp | level | logger | message
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
