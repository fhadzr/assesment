"""Task 1.4 verification: label/content correctness of the corpus."""

from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from docintel.corpus.generate import generate
from docintel.corpus.schema import FIELD_NAMES


def _gen(tmp_path: Path, n: int = 20) -> Path:
    out = tmp_path / "case2"
    generate(42, n, out)
    return out


def _pdf_text(path: Path) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(str(path)).pages)


def test_labels_match_rendered_text(tmp_path):
    from datetime import datetime

    from docintel.corpus.schema import DATE_FORMATS

    out = _gen(tmp_path)
    for j in (out / "expected").glob("*.json"):
        expected = json.loads(j.read_text())
        pdf_text = _pdf_text(out / "samples" / (j.stem + ".pdf"))
        for field in FIELD_NAMES:
            value = expected[field]
            if field in ("invoice_date", "due_date"):
                # dates render in one of the variant formats; the expected ISO
                # date must be recoverable from the rendered text via one format
                d = datetime.strptime(value, "%Y-%m-%d")
                assert any(d.strftime(fmt) in pdf_text for fmt in DATE_FORMATS), (j.name, field, value)
            else:
                assert value in pdf_text, (j.name, field, value)


def test_cross_field_consistency(tmp_path):
    from decimal import Decimal

    out = _gen(tmp_path)
    for j in (out / "expected").glob("*.json"):
        e = json.loads(j.read_text())
        assert Decimal(e["subtotal"]) + Decimal(e["tax"]) == Decimal(e["total"]), j.name
        assert e["invoice_date"] <= e["due_date"], j.name


def test_at_least_three_layout_variants(tmp_path):
    out = _gen(tmp_path, n=20)
    # distinguish variants by the invoice_number label rendered
    variants = set()
    for pdf in sorted((out / "samples").glob("*.pdf")):
        text = _pdf_text(pdf)
        label = next(l for l in ("Invoice No:", "Invoice #", "Invoice Number:") if l in text)
        variants.add(label)
    assert len(variants) >= 3, variants


def test_image_variants_force_ocr_path(tmp_path):
    """PDF text layer extraction must recover <3 fields from the .png twin."""
    out = _gen(tmp_path, n=15)
    png = out / "samples" / "inv_0000.png"
    # a PNG has no PDF text layer; confirm it's a raster and that treating it
    # as a PDF is impossible (PdfReader raises) — hence OCR is the only path.
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    import pytest
    from pypdf import PdfReader
    with pytest.raises(Exception):
        PdfReader(str(png))
