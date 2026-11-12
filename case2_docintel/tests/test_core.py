"""Task 2.7 verification: pipeline composition + review routing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docintel.core import extract_document
from docintel.corpus.generate import generate
from docintel.providers import MockProvider


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("case2")
    generate(42, 15, out)
    return out


def test_text_pdf_ok_status(corpus):
    pdf = corpus / "samples" / "inv_0000.pdf"
    result = extract_document(pdf.name, pdf.read_bytes(), MockProvider())
    assert result.status == "ok"
    assert all(s == "extracted" for s in result.field_statuses.values())
    assert result.review == []


def test_review_queue_on_missing_field(corpus, monkeypatch):
    class MissingTotalProvider(MockProvider):
        def extract(self, masked_text):
            out = super().extract(masked_text)
            out.fields["total"] = None
            return out

    pdf = corpus / "samples" / "inv_0000.pdf"
    result = extract_document(pdf.name, pdf.read_bytes(), MissingTotalProvider())
    assert result.status == "review"
    entry = next(e for e in result.review if e.field == "total")
    assert entry.status == "missing"
    assert entry.document_id == "inv_0000"
    assert entry.reason


def test_review_entry_self_contained(corpus, monkeypatch):
    class BadDate(MockProvider):
        def extract(self, masked_text):
            out = super().extract(masked_text)
            out.fields["due_date"] = "2026-01-01"
            return out

    pdf = corpus / "samples" / "inv_0000.pdf"
    result = extract_document(pdf.name, pdf.read_bytes(), BadDate())
    entry = next(e for e in result.review if e.field == "due_date")
    assert entry.value == "2026-01-01"
    assert entry.status == "invalid"
    assert "invoice_date after due_date" in entry.reason


def test_image_doc_ocr_unavailable_when_no_binary(corpus, monkeypatch):
    import docintel.pipeline as pipeline

    monkeypatch.setattr(pipeline, "ocr_available", lambda: False)
    png = corpus / "samples" / "inv_0000.png"
    result = extract_document(png.name, png.read_bytes(), MockProvider())
    assert result.status == "ocr_unavailable"
    assert all(v is None for v in result.fields.values())


def test_review_report_artifact_serializable(corpus):
    pdf = corpus / "samples" / "inv_0000.pdf"
    result = extract_document(pdf.name, pdf.read_bytes(), MockProvider())
    # a review report is just the serialized results; ensure it round-trips
    import dataclasses
    payload = json.dumps(dataclasses.asdict(result))
    assert json.loads(payload)["document_id"] == "inv_0000"
