"""Structured logging foundation with request_id correlation and secret redaction.

Follows `docs/06-security-specification.md`, `docs/10-deployment-and-devops-specification.md`,
and `docs/11-project-structure-and-coding-standards.md` (Section 24).
"""

from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar
from typing import Any

from app.core.time_utils import utc_now_iso

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")

REDACTED_PLACEHOLDER = "[REDACTED]"

SENSITIVE_KEY_NAMES: frozenset[str] = frozenset(
    {
        "password",
        "current_password",
        "new_password",
        "password_hash",
        "secret",
        "jwt_secret_key",
        "csrf_secret_key",
        "access_token",
        "refresh_token",
        "customer_session_token",
        "qr_token",
        "token_hash",
        "authorization",
        "cookie",
        "set-cookie",
        "x-customer-session",
        "x-customer-session-token",
        "x-csrf-token",
        "database_url",
    }
)

# Regex patterns to scrub inline bearer tokens, session tokens, or DB URLs from log strings
INLINE_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
        rf"\1{REDACTED_PLACEHOLDER}",
    ),
    (
        re.compile(
            r"(postgresql(?:\+asyncpg)?://[^:\s]+:)([^@\s]+)(@)",
            re.IGNORECASE,
        ),
        rf"\1{REDACTED_PLACEHOLDER}\3",
    ),
    (
        re.compile(
            r"((?:password|secret|token|jwt_secret_key|csrf_secret_key)\s*[=:]\s*['\"]?)([^'\"\s,&]+)",
            re.IGNORECASE,
        ),
        rf"\1{REDACTED_PLACEHOLDER}",
    ),
)


def redact_sensitive_text(text: str) -> str:
    """Scrub inline secrets, Bearer JWTs, and database passwords from a string."""
    sanitized = text
    for pattern, replacement in INLINE_SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def redact_sensitive_data(value: Any) -> Any:
    """Recursively redact sensitive keys and patterns in dicts, lists, and strings."""
    if isinstance(value, dict):
        sanitized_dict: dict[str, Any] = {}
        for k, v in value.items():
            key_lower = str(k).lower().strip()
            if key_lower in SENSITIVE_KEY_NAMES or any(
                sensitive in key_lower
                for sensitive in ("password", "secret", "token", "authorization", "cookie")
            ):
                sanitized_dict[k] = REDACTED_PLACEHOLDER
            else:
                sanitized_dict[k] = redact_sensitive_data(v)
        return sanitized_dict
    if isinstance(value, list | tuple):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value


class SecretRedactionFilter(logging.Filter):
    """Logging filter that injects `request_id` and scrubs sensitive data."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get("-")
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_sensitive_data(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(redact_sensitive_data(arg) for arg in record.args)
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            record.extra_data = redact_sensitive_data(record.extra_data)
        return True


class StructuredJsonFormatter(logging.Formatter):
    """JSON log formatter for structured observability."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", request_id_ctx_var.get("-"))
        payload: dict[str, Any] = {
            "timestamp": utc_now_iso(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id,
            "message": redact_sensitive_text(record.getMessage()),
        }
        extra_data = getattr(record, "extra_data", None)
        if isinstance(extra_data, dict) and extra_data:
            payload["context"] = redact_sensitive_data(extra_data)
        if record.exc_info:
            payload["exception"] = redact_sensitive_text(self.formatException(record.exc_info))
        return json.dumps(payload, default=str)


class ConsoleStructuredFormatter(logging.Formatter):
    """Readable single-line structured formatter for local development and tests."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", request_id_ctx_var.get("-"))
        message = redact_sensitive_text(record.getMessage())
        base = (
            f"{utc_now_iso()} | {record.levelname:<8} | "
            f"req_id={request_id} | {record.name} | {message}"
        )
        extra_data = getattr(record, "extra_data", None)
        if isinstance(extra_data, dict) and extra_data:
            base += f" | context={json.dumps(redact_sensitive_data(extra_data), default=str)}"
        if record.exc_info:
            base += f"\n{redact_sensitive_text(self.formatException(record.exc_info))}"
        return base


def configure_logging(log_level: str = "INFO", json_output: bool = False) -> None:
    """Configure root and application loggers with secret redaction."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(SecretRedactionFilter())
    if json_output:
        handler.setFormatter(StructuredJsonFormatter())
    else:
        handler.setFormatter(ConsoleStructuredFormatter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Quiet noisy third-party loggers while keeping uvicorn access/error routed cleanly
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.error").handlers = [handler]
    logging.getLogger("uvicorn.error").propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a named application logger."""
    return logging.getLogger(name)
