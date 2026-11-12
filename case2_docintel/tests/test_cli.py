"""Task 3.2 verification: CLI batch + API/CLI agreement."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docintel.cli import main as cli_main
from docintel.corpus.generate import generate
from docintel.service.app import create_app


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("case2")
    generate(42, 15, out)
    return out


def test_batch_over_corpus(corpus, tmp_path):
    out = tmp_path / "results.json"
    rc = cli_main(["--in", str(corpus / "samples"), "--out", str(out), "--provider", "mock"])
    assert rc == 0
    data = json.loads(out.read_text())
    assert len(data) >= 15  # 15 PDFs (+15 PNGs may be skipped as OCR-unavailable, still counted)
    assert all("fields" in d and "field_statuses" in d for d in data)


def test_cli_api_agree_on_same_file(corpus, tmp_path):
    pdf = corpus / "samples" / "inv_0000.pdf"
    out = tmp_path / "one.json"
    rc = cli_main(["--in", str(pdf), "--out", str(out), "--provider", "mock"])
    assert rc == 0
    cli_result = json.loads(out.read_text())[0]

    tc = TestClient(create_app())
    r = tc.post("/extract", files={"file": ("inv_0000.pdf", pdf.read_bytes(), "application/pdf")})
    api_result = r.json()
    assert cli_result["fields"] == api_result["fields"]
    assert cli_result["field_statuses"] == api_result["field_statuses"]
    assert cli_result["status"] == api_result["status"]


def test_empty_dir_exits_nonzero(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    rc = cli_main(["--in", str(empty), "--out", str(tmp_path / "o.json"), "--provider", "mock"])
    assert rc == 2
    assert not (tmp_path / "o.json").exists()
