"""FastAPI extraction service (task 3.1).

Upload validation BEFORE parsing: extension allowlist + magic-byte type check
+ 5 MB size limit. PII-safe logging (request id + outcome only).
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from docintel.core import extract_document
from docintel.pipeline import PDF_EXTENSIONS, IMAGE_EXTENSIONS, is_image, is_pdf

ALLOWED_EXTENSIONS = PDF_EXTENSIONS | IMAGE_EXTENSIONS
MAX_BYTES = 5 * 1024 * 1024  # 5 MB

logger = logging.getLogger("docintel.service")


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return getattr(record, "structured", False)


def _setup_logging() -> None:
    if any(isinstance(h, logging.StreamHandler) and getattr(h, "docintel", False) for h in logger.handlers):
        return
    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter())
    handler.docintel = True
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _log_outcome(outcome: str) -> None:
    logger.info("request_id=%s outcome=%s", f"req-{uuid.uuid4().hex[:12]}", outcome, extra={"structured": True})


async def _read_limited(file: UploadFile) -> bytes:
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="upload exceeds 5 MB limit")
    return content


def _validate_content(filename: str, content: bytes) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"unsupported extension '{ext}'; allowed: {sorted(ALLOWED_EXTENSIONS)}")
    # magic-byte check: extension must match actual content
    if ext in PDF_EXTENSIONS and not is_pdf(type("D", (), {"content": content})()):
        raise HTTPException(status_code=422, detail="content is not a valid PDF despite .pdf extension")
    if ext in IMAGE_EXTENSIONS and not is_image(type("D", (), {"content": content})()):
        raise HTTPException(status_code=422, detail="content is not a valid image despite its extension")


def create_app(provider=None) -> FastAPI:
    from docintel.providers import MockProvider

    provider = provider or MockProvider()
    _setup_logging()
    app = FastAPI(title="docintel-extraction", version="1.0.0")
    app.state.provider = provider

    @app.post("/extract")
    async def extract(file: UploadFile):
        content = await _read_limited(file)
        try:
            _validate_content(file.filename or "", content)
        except HTTPException:
            raise
        result = extract_document(file.filename or "upload", content, app.state.provider)
        _log_outcome(f"extracted status={result.status}")
        return {
            "document_id": result.document_id,
            "status": result.status,
            "fields": result.fields,
            "field_statuses": result.field_statuses,
            "review": [vars(e) for e in result.review],
            "usage": result.usage,
        }

    @app.get("/model-info")
    async def model_info():
        return {"provider": app.state.provider.name}

    return app
