"""Task 4.1 verification: FastAPI /ask."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rag.generate_kb import generate
from rag.service.app import create_app


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    out = tmp_path_factory.mktemp("data")
    generate(42, 10, out)
    app = create_app(str(out / "kb.json"))
    return TestClient(app)


def test_valid_ask(client):
    r = client.post("/ask", json={"question": "What is the annual leave entitlement?", "role": "hr"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert isinstance(body["citations"], list)
    assert isinstance(body["refusal"], bool)


def test_missing_role_422(client):
    r = client.post("/ask", json={"question": "q"})
    assert r.status_code == 422
    assert "Traceback" not in r.text


def test_invalid_role_422(client):
    r = client.post("/ask", json={"question": "q", "role": "superuser"})
    assert r.status_code == 422
    assert "Traceback" not in r.text


def test_missing_question_422(client):
    r = client.post("/ask", json={"role": "hr"})
    assert r.status_code == 422


def test_no_500_on_validation(client):
    r = client.post("/ask", json={"question": "", "role": "hr"})
    assert 400 <= r.status_code < 500


def test_model_info(client):
    info = client.get("/model-info").json()
    assert info["provider"] == "mock"
    assert set(info["roles"]) == {"hr", "finance", "exec"}
