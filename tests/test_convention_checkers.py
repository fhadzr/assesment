"""Tests for the convention checker scripts (pass and fail paths).

Run with any interpreter that has pytest; the checkers are stdlib-only.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def _load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


check_data = _load("check_data_conventions", SCRIPTS / "check_data_conventions.py")
check_evidence = _load("check_evidence_conventions", SCRIPTS / "check_evidence_conventions.py")


@pytest.fixture()
def sandbox(tmp_path: Path) -> Path:
    """Minimal repo skeleton the checkers accept."""
    (tmp_path / "evidence").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "case1_fraud" / "data").mkdir(parents=True)
    (tmp_path / "case1_fraud" / "src").mkdir(parents=True)
    (tmp_path / "case2_docintel" / "samples").mkdir(parents=True)
    (tmp_path / "case3_rag" / "data").mkdir(parents=True)
    with (tmp_path / "evidence" / "assessment_traceability.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        csv.writer(f).writerow(check_evidence.EXPECTED_COLUMNS)
    return tmp_path


# --- data checker: pass path ---


def test_data_check_passes_on_empty_repo(sandbox: Path):
    assert check_data.run_check(sandbox) == []


# --- data checker: fail paths ---


def test_data_check_flags_hand_authored_file_without_generator(sandbox: Path):
    (sandbox / "case1_fraud" / "data" / "hand.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    violations = check_data.run_check(sandbox)
    assert any(v.startswith("R1") for v in violations)


def test_data_check_flags_ssn_in_data_file(sandbox: Path):
    gen = sandbox / "case1_fraud" / "src" / "generate_data.py"
    gen.write_text("def main():\n    seed = 42\n", encoding="utf-8")
    (sandbox / "case1_fraud" / "data" / "rows.csv").write_text(
        "note\n'111-22-3333'\n", encoding="utf-8"
    )
    violations = check_data.run_check(sandbox)
    assert any(v.startswith("R3") for v in violations)


def test_data_check_flags_generator_without_seed(sandbox: Path):
    (sandbox / "case1_fraud" / "src" / "generate_data.py").write_text(
        "print('hardcoded randomness, nothing configurable')\n", encoding="utf-8"
    )
    violations = check_data.run_check(sandbox)
    assert any(v.startswith("R2") for v in violations)


# --- evidence checker: pass path ---


def test_evidence_check_passes_on_clean_sandbox(sandbox: Path):
    assert check_evidence.run_check(sandbox) == []


# --- evidence checker: fail paths ---


def test_evidence_check_flags_wrong_column_count(sandbox: Path):
    matrix = sandbox / "evidence" / "assessment_traceability.csv"
    rows = list(csv.reader(matrix.open(newline="", encoding="utf-8")))
    rows.append(["only", "three", "cols"])
    with matrix.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    violations = check_evidence.run_check(sandbox)
    assert any(v.startswith("E1") for v in violations)


def test_evidence_check_flags_bad_status(sandbox: Path):
    matrix = sandbox / "evidence" / "assessment_traceability.csv"
    rows = list(csv.reader(matrix.open(newline="", encoding="utf-8")))
    row = ["" for _ in check_evidence.EXPECTED_COLUMNS]
    row[9] = "maybe"
    rows.append(row)
    with matrix.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    violations = check_evidence.run_check(sandbox)
    assert any(v.startswith("E2") for v in violations)


def test_evidence_check_flags_verified_row_with_missing_path(sandbox: Path):
    matrix = sandbox / "evidence" / "assessment_traceability.csv"
    rows = list(csv.reader(matrix.open(newline="", encoding="utf-8")))
    row = ["" for _ in check_evidence.EXPECTED_COLUMNS]
    row[7] = "case1_fraud/tests/does_not_exist.py"
    row[9] = "verified"
    rows.append(row)
    with matrix.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    violations = check_evidence.run_check(sandbox)
    assert any(v.startswith("E3") for v in violations)


def test_evidence_check_allows_pending_row_with_missing_paths(sandbox: Path):
    matrix = sandbox / "evidence" / "assessment_traceability.csv"
    rows = list(csv.reader(matrix.open(newline="", encoding="utf-8")))
    row = ["" for _ in check_evidence.EXPECTED_COLUMNS]
    row[7] = "case1_fraud/tests/future_test.py"
    row[9] = "pending"
    rows.append(row)
    with matrix.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    assert check_evidence.check_matrix(sandbox) == []


# --- secret scan ---


def test_secret_scan_flags_planted_key(sandbox: Path):
    planted = sandbox / "case1_fraud" / "src" / "config.py"
    planted.write_text(
        'API_KEY = "sk-PLANTEDFAKEKEY1234567890abcd"\n', encoding="utf-8"
    )
    violations = check_evidence.scan_secrets(sandbox)
    assert any(v.startswith("S1") for v in violations)


def test_secret_scan_passes_on_benign_source(sandbox: Path):
    planted = sandbox / "case1_fraud" / "src" / "config.py"
    planted.write_text(
        "API_KEY = os.environ['GROQ_API_KEY']\n", encoding="utf-8"
    )
    assert check_evidence.scan_secrets(sandbox) == []
