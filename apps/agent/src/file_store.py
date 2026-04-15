"""Process-wide store for uploaded documents, keyed by thread_id."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StoredDoc:
    filename: str
    mime_type: str
    content: str
    uploaded_at: int


# thread_id -> list[StoredDoc]
UPLOADED_DOCS: dict[str, list[StoredDoc]] = {}
