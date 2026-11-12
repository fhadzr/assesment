"""Tasks 4.1 + 4.2: security posture (disguised uploads, size, PII-safe logs, routes)."""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docintel.corpus.generate import generate
from docintel.service.app import create_app

RAW_MARKERS = ("Amberline Trading", "billing@amberline-example.com", "+1-555-010-0692", "ACC-8935-1424")


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("case2")
    generate(42, 15, out)
    return out


@pytest.fixture()
def log_stream():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("docintel.service")
    logger.addHandler(handler)
    yield stream, logger
    logger.removeHandler(handler)


def test_disguised_upload_rejected(client_corpus=None):
    tc = TestClient(create_app())
    # ELF with .pdf name
    r = tc.post("/extract", files={"file": ("evil.pdf", b"\x7fELF" + b"\x00" * 60, "application/pdf")})
    assert r.status_code == 422
    # HTML/script with .pdf name (polyglot-ish)
    r2 = tc.post("/extract", files={"file": ("page.pdf", b"<html><script>alert(1)</script></html>", "application/pdf")})
    assert r2.status_code == 422


def test_size_limit_rejected():
    tc = TestClient(create_app())
    big = b"%PDF-1.3\n" + b"x" * (6 * 1024 * 1024)
    r = tc.post("/extract", files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413


def test_pii_safe_logging(corpus, log_stream):
    stream, _ = log_stream
    tc = TestClient(create_app())
    pdf = (corpus / "samples" / "inv_0000.pdf").read_bytes()
    tc.post("/extract", files={"file": ("inv_0000.pdf", pdf, "application/pdf")})
    tc.post("/extract", files={"file": ("evil.pdf", b"\x7fELF" + b"\x00" * 60, "application/pdf")})
    content = stream.getvalue()
    for marker in RAW_MARKERS:
        assert marker not in content, f"{marker!r} leaked into logs"
    assert "extracted status=" in content  # outcome logged


@pytest.mark.parametrize("path", ["/debug", "/admin"])
def test_undeclared_routes_404(path):
    tc = TestClient(create_app())
    assert tc.get(path).status_code == 404


def test_no_debug_routes_in_openapi():
    tc = TestClient(create_app())
    paths = set(tc.get("/openapi.json").json()["paths"])
    assert paths == {"/extract", "/model-info"}, paths
