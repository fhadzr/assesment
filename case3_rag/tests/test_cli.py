"""Task 4.2 verification: CLI batch + CLI/API agreement."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rag.cli import main as cli_main
from rag.generate_eval import generate as eval_generate
from rag.generate_kb import generate as kb_generate
from rag.service.app import create_app


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    out = tmp_path_factory.mktemp("data")
    kb_generate(42, 10, out)
    eval_generate(42, 36, out)
    return out


def test_batch_one_result_per_question(data, tmp_path):
    out = tmp_path / "results.json"
    rc = cli_main(["--in", str(data / "eval.json"), "--kb", str(data / "kb.json"),
                   "--out", str(out), "--provider", "mock"])
    assert rc == 0
    results = json.loads(out.read_text())
    assert len(results) == 36
    assert all("answer" in r and "refusal" in r and "citations" in r for r in results)


def test_cli_api_agree(data, tmp_path):
    q = json.loads((data / "eval.json").read_text())[0]
    out = tmp_path / "one.json"
    rc = cli_main(["--in", str(data / "eval.json"), "--kb", str(data / "kb.json"),
                   "--out", str(out), "--provider", "mock"])
    assert rc == 0
    cli_result = json.loads(out.read_text())[0]

    tc = TestClient(create_app(str(data / "kb.json")))
    r = tc.post("/ask", json={"question": q["question"], "role": q["role"]})
    api_result = r.json()
    assert cli_result["answer"] == api_result["answer"]
    assert cli_result["citations"] == api_result["citations"]
    assert cli_result["refusal"] == api_result["refusal"]


def test_invalid_role_cli_rejected(data, tmp_path):
    # CLI role validation happens at ask() via the core; a batch has per-question roles.
    # Exercise the provider/role path with an eval containing a bogus role.
    bad = tmp_path / "bad.json"
    qs = json.loads((data / "eval.json").read_text())
    qs[0]["role"] = "superuser"
    bad.write_text(json.dumps(qs))
    out = tmp_path / "o.json"
    rc = cli_main(["--in", str(bad), "--kb", str(data / "kb.json"),
                   "--out", str(out), "--provider", "mock"])
    assert rc == 0  # batch completes; the bad role yields a refused/error entry
    results = json.loads(out.read_text())
    assert results[0]["error"] and "invalid role" in results[0]["error"]
