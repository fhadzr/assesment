"""Task 2.1 verification: PDF text extraction path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docintel.corpus.generate import generate
from docintel.pipeline import Document, extract_pdf_text, is_pdf
from docintel.corpus.schema import FIELD_NAMES


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("case2")
    generate(42, 15, out)
    return out


def test_text_pdf_extracts_six_of_eight(corpus):
    pdf = corpus / "samples" / "inv_0000.pdf"
    doc = Document(filename=pdf.name, content=pdf.read_bytes())
    assert is_pdf(doc)
    text = extract_pdf_text(doc)
    expected = json.loads((corpus / "expected" / "inv_0000.json").read_text())
    found = sum(1 for f in FIELD_NAMES if expected[f] in text or (f in ("invoice_date", "due_date") and expected[f][:4] in text))
    # invoice_number + vendor + subtotal/tax/total + currency always verbatim
    assert found >= 6, f"only {found}/8 fields in extracted text"


def test_corrupt_file_raises_no_partial_success():
    doc = Document(filename="bad.pdf", content=b"not a pdf at all")
    with pytest.raises(Exception):
        extract_pdf_text(doc)


def test_non_pdf_detected():
    assert not is_pdf(Document(filename="x.pdf", content=b"\x89PNG..."))


def test_image_variant_is_not_pdf(corpus):
    png = corpus / "samples" / "inv_0000.png"
    doc = Document(filename=png.name, content=png.read_bytes())
    assert not is_pdf(doc)
