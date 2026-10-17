"""Input sanitization utilities for XSS and injection prevention.

Follows `docs/06-security-specification.md` (Section 24):
  - Reject HTML tag delimiters (`<`, `>`) from all user text inputs.
  - Reject `javascript:` and `data:` URI schemes.
  - Strip null bytes and control characters (except newline/tab).

All Pydantic request models that accept free-text fields (notes, reasons,
names, descriptions) should pass their string fields through `sanitize_text`.
"""

from __future__ import annotations

import re

# HTML tag pattern: anything opening or closing an HTML tag
_HTML_TAG_RE = re.compile(r"[<>]")

# Dangerous URI schemes (XSS via href/src attributes)
_DANGEROUS_URI_RE = re.compile(r"(?i)(javascript|data|vbscript):")

# Null bytes and non-printable ASCII control characters (except \t \n \r)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(value: str | None) -> str | None:
    """Strip HTML tags, dangerous URI schemes, and control characters from a text field.

    Returns None if the input is None.
    Raises ValueError if the input contains HTML tag characters after stripping.
    """
    if value is None:
        return None

    # Strip null bytes and control chars (silent removal — they are never intentional)
    cleaned = _CONTROL_CHARS_RE.sub("", value)

    # Reject dangerous URI schemes first (defence-in-depth; React/Flutter would also escape these)
    if _DANGEROUS_URI_RE.search(cleaned):
        raise ValueError(
            "Text fields must not contain dangerous URI schemes (javascript:, data:, vbscript:)."
        )

    # Reject HTML tag delimiters — these are never valid in plain-text fields
    if _HTML_TAG_RE.search(cleaned):
        raise ValueError("Text fields must not contain HTML tag characters (`<` or `>`).")

    return cleaned


def sanitize_text_field(value: str | None) -> str | None:
    """Pydantic-compatible field_validator wrapper for sanitize_text."""
    return sanitize_text(value)
