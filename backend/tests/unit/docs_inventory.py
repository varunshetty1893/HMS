"""Parse the canonical schema inventory out of `docs/04-database-design.md`.

The tests compare SQLAlchemy metadata against what the documentation actually says instead of
against a hand-copied list, so the traceability cannot silently drift.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

DOC_PATH = Path(__file__).resolve().parents[3] / "docs" / "04-database-design.md"

_CATALOG_ROW = re.compile(r"^\| \*\*(\d+)\*\* \| \*\*`(\w+)`\*\* \|")
_HEADING = re.compile(r"^#{2,4} ")
_FIELD_LINE = re.compile(r"^\s+- `(\w+)` \(`([A-Za-z]+(?:\(\d+(?:, ?\d+)?\))?)`")
_NAMES = re.compile(r"`(\w+)`")


@dataclass
class DocTable:
    name: str
    number: int
    required: set[str] = field(default_factory=set)
    optional: set[str] = field(default_factory=set)
    detail_types: dict[str, str] = field(default_factory=dict)  # column -> documented SQL type
    detail_columns: set[str] = field(default_factory=set)


def normalize_type(sql_type: str) -> str:
    """Normalize a documented or compiled SQL type for comparison."""
    value = sql_type.upper().replace(" ", "")
    return {
        "TIMESTAMPTZ": "TIMESTAMPWITHTIMEZONE",
        "TIMESTAMP WITH TIME ZONE": "TIMESTAMPWITHTIMEZONE",
        "TIMESTAMPWITHTIMEZONE": "TIMESTAMPWITHTIMEZONE",
        "INT": "INTEGER",
    }.get(value, value)


def load_doc_inventory() -> dict[str, DocTable]:
    lines = DOC_PATH.read_text(encoding="utf-8").splitlines()
    tables: dict[str, DocTable] = {}

    for line in lines:
        match = _CATALOG_ROW.match(line)
        if not match:
            continue
        number, name = int(match.group(1)), match.group(2)
        cells = [cell.strip() for cell in line.split("|")]
        # cells: ['', '**1**', '**`users`**', purpose, PK, FKs, Req/Opt, unique, check, ...]
        req_opt = cells[6]
        table = DocTable(name=name, number=number)
        for part in req_opt.split("<br>"):
            names = set(_NAMES.findall(part))
            if part.startswith("**Req:**"):
                table.required = names
            elif part.startswith("**Opt:**"):
                table.optional = names
        tables[name] = table

    current: DocTable | None = None
    for line in lines:
        if _HEADING.match(line):
            current = None
            for candidate in _NAMES.findall(line):
                if candidate in tables:
                    current = tables[candidate]
                    break
            continue
        if current is None:
            continue
        field_match = _FIELD_LINE.match(line)
        if field_match:
            column, sql_type = field_match.groups()
            current.detail_columns.add(column)
            current.detail_types[column] = sql_type
    return tables
