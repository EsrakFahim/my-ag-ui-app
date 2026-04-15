"""Custom HTTP routes mounted into the LangGraph dev server.

Exposes:
  POST   /documents/upload      -- multipart upload (file + thread_id)
  DELETE /documents/{thread_id} -- clear all docs for a thread
  GET    /documents/{thread_id} -- list docs for a thread (debug)
"""

from __future__ import annotations

import importlib
import io
import json
import os
import time
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.file_store import UPLOADED_DOCS, StoredDoc

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_DOC_CHARS = 80_000
SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".mdx",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".log",
    ".xml",
    ".html",
    ".css",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".pdf",
}


def _ext(name: str) -> str:
    return os.path.splitext(name.lower())[1]


def _extract_text(filename: str, raw: bytes) -> str:
    ext = _ext(filename)
    if ext == ".pdf":
        pypdf = importlib.import_module("pypdf")
        reader = pypdf.PdfReader(io.BytesIO(raw))
        return "\n\n".join((p.extract_text() or "") for p in reader.pages)
    if ext == ".json":
        parsed = json.loads(raw.decode("utf-8", errors="replace"))
        return json.dumps(parsed, indent=2, ensure_ascii=True)
    return raw.decode("utf-8", errors="replace")


router = APIRouter()


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    thread_id: str = Form(...),
) -> dict[str, Any]:
    if not thread_id:
        raise HTTPException(400, "thread_id is required")

    filename = file.filename or "uploaded-file"
    ext = _ext(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    raw = await file.read()
    if not raw:
        raise HTTPException(400, "File is empty")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "File too large (5MB max)")

    try:
        text = _extract_text(filename, raw).strip()
    except Exception as exc:
        raise HTTPException(400, f"Parse error: {exc}") from exc

    if not text:
        raise HTTPException(400, "No readable text in file")

    text = text[:MAX_DOC_CHARS]
    doc = StoredDoc(
        filename=filename,
        mime_type=file.content_type or "text/plain",
        content=text,
        uploaded_at=int(time.time()),
    )

    bucket = UPLOADED_DOCS.setdefault(thread_id, [])
    bucket.append(doc)
    if len(bucket) > 8:
        del bucket[:-8]

    return {
        "status": "success",
        "thread_id": thread_id,
        "filename": filename,
        "size_bytes": len(raw),
        "count": len(bucket),
    }


@router.delete("/documents/{thread_id}")
async def clear_documents(thread_id: str) -> dict[str, str]:
    UPLOADED_DOCS.pop(thread_id, None)
    return {"status": "ok"}


@router.get("/documents/{thread_id}")
async def list_documents(thread_id: str) -> dict[str, Any]:
    docs = UPLOADED_DOCS.get(thread_id, [])
    return {
        "thread_id": thread_id,
        "count": len(docs),
        "documents": [
            {
                "filename": d.filename,
                "mime_type": d.mime_type,
                "size": len(d.content),
                "uploaded_at": d.uploaded_at,
            }
            for d in docs
        ],
    }
