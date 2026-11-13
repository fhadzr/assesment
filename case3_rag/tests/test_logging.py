"""Task 5.2 verification: PII-safe logging."""

from __future__ import annotations

import io
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rag.generate_kb import generate
from rag.service.app import create_app

RAW_MARKERS = ("leave_policy", "retained for 7 years", "salary_bands", "exec_budget")


@pytest.fixture()
def log_stream():
    stream = io.StringIO()
    h = logging.StreamHandler(stream)
    logger = logging.getLogger("rag.service")
    logger.addHandler(h)
    yield stream, logger
    logger.removeHandler(h)


def test_no_document_text_in_logs(tmp_path, log_stream):
    stream, _ = log_stream
    out = tmp_path / "data"
    generate(42, 10, out)
    tc = TestClient(create_app(str(out / "kb.json")))
    tc.post("/ask", json={"question": "annual leave entitlement", "role": "hr"})
    tc.post("/ask", json={"question": "audit retention", "role": "hr"})
    content = stream.getvalue()
    for marker in RAW_MARKERS:
        assert marker not in content, f"{marker!r} leaked into logs"
    assert "asked refusal=" in content  # outcome logged


def test_no_pii_in_logs(tmp_path, log_stream):
    stream, _ = log_stream
    out = tmp_path / "data"
    generate(42, 10, out)
    tc = TestClient(create_app(str(out / "kb.json")))
    tc.post("/ask", json={"question": "q", "role": "superuser"})  # rejected request too
    assert "superuser" not in stream.getvalue()
