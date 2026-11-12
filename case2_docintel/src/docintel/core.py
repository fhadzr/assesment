"""Shared extraction core (tasks 2.7 + 3.1 + 3.2).

Composes the pipeline stages into one function used identically by the API
and the CLI (agreement pinned by tests):

  ingest -> extract_text(pdf|ocr) -> mask -> llm_extract -> validate -> route
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from docintel.corpus.schema import FIELD_NAMES
from docintel.masking import mask_pii
from docintel.pipeline import (
    Document,
    extract_image_text_ocr,
    extract_pdf_text,
    is_image,
    is_pdf,
    ocr_available,
)
from docintel.providers import ProviderError
from docintel.validation import ReviewEntry, validate_fields

DOCUMENT_STATUSES = ("ok", "review", "ocr_unavailable", "extraction_error", "ingest_error")


@dataclass
class ExtractionResult:
    document_id: str
    status: str
    fields: dict[str, str | None] = field(default_factory=dict)
    field_statuses: dict[str, str] = field(default_factory=dict)
    review: list[ReviewEntry] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    error: str | None = None


def _document_id(filename: str, idx: int | None = None) -> str:
    stem = Path(filename).stem
    return stem or f"doc_{idx}"


def extract_document(filename: str, content: bytes, provider, doc_id: str | None = None) -> ExtractionResult:
    doc = Document(filename=filename, content=content)
    did = doc_id or _document_id(filename)

    # 1. ingest + type detection
    if is_pdf(doc):
        try:
            text = extract_pdf_text(doc)
        except Exception as exc:
            return ExtractionResult(document_id=did, status="ingest_error", error=f"PDF parse failed: {exc}")
    elif is_image(doc):
        if not ocr_available():
            return ExtractionResult(
                document_id=did, status="ocr_unavailable",
                error="Tesseract binary not installed; see docs/ocr_setup.md",
                fields={f: None for f in FIELD_NAMES},
            )
        try:
            text = extract_image_text_ocr(doc)
        except Exception as exc:
            return ExtractionResult(document_id=did, status="ingest_error", error=f"OCR failed: {exc}")
    else:
        return ExtractionResult(
            document_id=did, status="ingest_error",
            error="unsupported content type (neither PDF nor image)",
        )

    # 2. mask PII before provider context
    masked = mask_pii(text)

    # 3. LLM structured extraction
    try:
        output = provider.extract(masked.text)
    except ProviderError as exc:
        return ExtractionResult(document_id=did, status="extraction_error", error=str(exc))

    # 4. validate + route
    statuses, queue = validate_fields(output.fields)
    doc_status = "ok" if all(s == "extracted" for s in statuses.values()) else "review"
    for e in queue:
        e.document_id = did

    return ExtractionResult(
        document_id=did,
        status=doc_status,
        fields=output.fields,
        field_statuses=statuses,
        review=queue,
        usage=output.usage,
    )
