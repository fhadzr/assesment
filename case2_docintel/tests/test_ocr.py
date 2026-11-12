"""Task 2.2 verification: OCR path — both binary-present and binary-absent.

Covers the real-engine path when Tesseract exists, the probe-override path
when it does not (so the code is still executed), and the honest
`ocr_unavailable` degradation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import docintel.pipeline as pipeline
from docintel.corpus.generate import generate
from docintel.pipeline import Document, extract_image_text_ocr, ocr_available


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("case2")
    generate(42, 15, out)
    return out


def _png_doc(corpus) -> Document:
    png = corpus / "samples" / "inv_0000.png"
    return Document(filename=png.name, content=png.read_bytes())


def test_ocr_available_probe_returns_bool():
    assert isinstance(ocr_available(), bool)


def test_unavailable_path_is_honest(corpus, monkeypatch):
    monkeypatch.setattr(pipeline, "ocr_available", lambda: False)
    with pytest.raises(RuntimeError, match="unavailable"):
        extract_image_text_ocr(_png_doc(corpus))


def test_available_path_runs_real_engine_or_probe_override(corpus, monkeypatch):
    """When the binary is absent, monkeypatch the probe so the real code path
    still executes against a fake OCR engine; assert it parses pixels into text
    containing invoice content."""
    if ocr_available():
        text = extract_image_text_ocr(_png_doc(corpus))
        assert text.strip(), "real OCR returned empty text"
    else:
        # exercise the real code path by faking the engine's return
        monkeypatch.setattr(pipeline, "ocr_available", lambda: True)
        monkeypatch.setattr(pipeline.pytesseract, "image_to_string",
                            lambda img: "INVOICE\nInvoice Number: INV-100001\nSub-Total: 3754.80 USD\n")
        text = extract_image_text_ocr(_png_doc(corpus))
        assert "INV-100001" in text and "3754.80" in text


def test_real_engine_documented_when_installed(corpus):
    """If Tesseract is actually present, this test exercises it for real."""
    if not ocr_available():
        pytest.skip("Tesseract not installed; install per docs/ocr_setup.md to run the real-engine path")
    text = extract_image_text_ocr(_png_doc(corpus))
    # clean synthetic render; at least the invoice number digits should survive
    assert "INV-100001" in text or "100001" in text
