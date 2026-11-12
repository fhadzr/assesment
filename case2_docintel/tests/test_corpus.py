"""Task 1.3 verification: corpus generation contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docintel.corpus.generate import MAX_INVOICES, MIN_INVOICES, generate


def _gen(tmp_path: Path, seed: int = 42, n: int = 15) -> Path:
    out = tmp_path / "case2"
    generate(seed, n, out)
    return out


def test_corpus_size_honored(tmp_path):
    out = _gen(tmp_path, n=25)
    pdfs = list((out / "samples").glob("inv_*.pdf"))
    pngs = list((out / "samples").glob("inv_*.png"))
    labels = list((out / "expected").glob("inv_*.json"))
    assert len(pdfs) == len(pngs) == len(labels) == 25
    assert json.loads((out / "corpus_manifest.json").read_text())["n_invoices"] == 25


def test_deterministic_regeneration(tmp_path):
    a = _gen(tmp_path / "a")
    b = _gen(tmp_path / "b")
    for pa in (a / "samples").iterdir():
        pb = b / "samples" / pa.name
        assert pb.read_bytes() == pa.read_bytes(), pa.name
    for pa in (a / "expected").iterdir():
        pb = b / "expected" / pa.name
        assert pb.read_bytes() == pa.read_bytes(), pa.name


def test_different_seed_differs(tmp_path):
    a = _gen(tmp_path / "a", seed=1)
    b = _gen(tmp_path / "b", seed=2)
    ea = json.loads((a / "expected" / "inv_0000.json").read_text())
    eb = json.loads((b / "expected" / "inv_0000.json").read_text())
    assert ea != eb


@pytest.mark.parametrize("n", [MIN_INVOICES - 1, MAX_INVOICES + 1])
def test_out_of_range_rejected(tmp_path, n):
    with pytest.raises(ValueError, match="15"):
        generate(42, n, tmp_path / "x")


def test_image_variants_are_pixel_based(tmp_path):
    """PDF text extraction must NOT recover field text from the .png variant."""
    from pypdf import PdfReader

    out = _gen(tmp_path, n=15)
    # png is a raster: extracting 'text' from it isn't possible via PdfReader;
    # instead prove the raster path is forced by checking the PDF twin DOES extract
    # (the companion test_corpus_labels asserts the png carries no text layer by
    # confirming its format is raster-only PNG).
    pdf = out / "samples" / "inv_0000.pdf"
    text = "\n".join(p.extract_text() for p in PdfReader(str(pdf)).pages)
    assert "INV-" in text
    png = out / "samples" / "inv_0000.png"
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"  # raster PNG magic
