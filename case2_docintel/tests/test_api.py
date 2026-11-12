"""Task 3.1 verification: FastAPI upload validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docintel.corpus.generate import generate
from docintel.service.app import MAX_BYTES, create_app


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("case2")
    generate(42, 15, out)
    return out


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def _pdf(corpus) -> bytes:
    return (corpus / "samples" / "inv_0000.pdf").read_bytes()


def test_valid_upload_extracts(client, corpus):
    r = client.post("/extract", files={"file": ("inv_0000.pdf", _pdf(corpus), "application/pdf")})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "review")
    assert set(body["fields"]) == {
        "invoice_number", "invoice_date", "vendor_name", "subtotal", "tax", "total", "currency", "due_date",
    }


def test_oversized_upload_413(client):
    big = b"%PDF-1.3\n" + b"x" * (MAX_BYTES + 10)
    r = client.post("/extract", files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413


def test_disguised_executable_rejected_by_magic_bytes(client):
    # named .pdf but content is an ELF header — not a valid PDF
    fake = b"\x7fELF\x02\x01\x01\x00" + b"junk" * 50
    r = client.post("/extract", files={"file": ("evil.pdf", fake, "application/pdf")})
    assert r.status_code == 422
    assert "not a valid PDF" in r.json()["detail"]


def test_unsupported_extension_rejected(client):
    r = client.post("/extract", files={"file": ("evil.exe", b"MZ" + b"\x00" * 60, "application/octet-stream")})
    assert r.status_code == 422
    assert "unsupported extension" in r.json()["detail"]


def test_image_doc_ocr_unavailable_honest(client, corpus, monkeypatch):
    import docintel.core as core

    monkeypatch.setattr(core, "ocr_available", lambda: False)
    png = (corpus / "samples" / "inv_0000.png").read_bytes()
    r = client.post("/extract", files={"file": ("inv_0000.png", png, "image/png")})
    assert r.status_code == 200
    assert r.json()["status"] == "ocr_unavailable"


def test_model_info(client):
    assert client.get("/model-info").json()["provider"] == "mock"
