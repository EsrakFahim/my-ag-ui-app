"""Persistent storage for uploaded documents, keyed by thread_id."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


UPLOAD_DIR = Path("uploaded_docs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class StoredDoc:
    filename: str
    mime_type: str
    content: str
    uploaded_at: int


# thread_id -> list[StoredDoc]
UPLOADED_DOCS: dict[str, list[StoredDoc]] = {}


def _thread_path(thread_id: str) -> Path:
    safe_thread_id = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in thread_id
    )
    return UPLOAD_DIR / f"{safe_thread_id}.json"


def save_docs(thread_id: str, docs: list[StoredDoc]) -> None:
    payload = [
        {
            "filename": doc.filename,
            "mime_type": doc.mime_type,
            "content": doc.content,
            "uploaded_at": doc.uploaded_at,
        }
        for doc in docs
    ]
    path = _thread_path(thread_id)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # Optional process cache for current process performance.
    UPLOADED_DOCS[thread_id] = docs


def load_docs(thread_id: str) -> list[StoredDoc]:
    path = _thread_path(thread_id)
    if not path.exists():
        return UPLOADED_DOCS.get(thread_id, [])

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    docs = [
        StoredDoc(
            filename=str(item.get("filename", "uploaded-file")),
            mime_type=str(item.get("mime_type", "text/plain")),
            content=str(item.get("content", "")),
            uploaded_at=int(item.get("uploaded_at", 0)),
        )
        for item in payload
        if isinstance(item, dict)
    ]
    # Keep in-memory cache, but disk remains source of truth.
    UPLOADED_DOCS[thread_id] = docs
    return docs


def clear_docs(thread_id: str) -> None:
    UPLOADED_DOCS.pop(thread_id, None)
    path = _thread_path(thread_id)
    if path.exists():
        path.unlink()
