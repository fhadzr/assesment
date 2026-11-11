#!/usr/bin/env python
"""Check V-TEKI evidence conventions (stdlib only).

Rules enforced (see docs/conventions/evidence.md):
  E1: the traceability matrix has exactly the ten defined columns, in order,
      with no malformed rows.
  E2: verification_status is one of pending | verified | failed.
  E3: any row marked verified must have all its non-empty path fields
      (implementation_location, test_location, evidence_artifact) resolve to
      existing files/directories.
  E4: evidence artifacts live only under evidence/ (heuristic: result/metrics/
      log JSON files outside evidence/ and outside outputs/ are flagged).
  S1: no secrets in tracked source: key-prefixed tokens (see SECRET_PATTERNS),
      api_key/apikey/secret/token assignments with literal values, and
      high-entropy strings, with an allowlist for false positives.

Exit code 0 = conventions hold; 1 = violations found (printed).
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

MATRIX_PATH = Path("evidence/assessment_traceability.csv")

EXPECTED_COLUMNS = [
    "requirement_id",
    "rubric_area",
    "criterion",
    "points",
    "case",
    "scenario_id",
    "implementation_location",
    "test_location",
    "evidence_artifact",
    "verification_status",
]

ALLOWED_STATUSES = {"pending", "verified", "failed"}

EVIDENCE_DIRS = {"experiment_log", "security_test_results", "cost_analysis"}

# Source suffixes the secret scan reads
SOURCE_SUFFIXES = {".py", ".toml", ".ini", ".cfg", ".yml", ".yaml", ".env.example", ".md", ".json"}

# Directories the secret scan skips (third-party, venvs, git, planning artifacts are prose)
SCAN_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", ".claude"}

SECRET_PATTERNS = [
    (re.compile(r"\b" + "sk" + r"-[A-Za-z0-9]{16,}\b"), "OpenAI-style key"),
    (re.compile(r"\bgsk_[A-Za-z0-9]{16,}\b"), "Groq-style key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"), "GitHub token"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "Slack token"),
]

ASSIGNMENT_RE = re.compile(
    r"""(?ix)\b(?:api_key|apikey|api_secret|secret|secret_key|password|passwd|access_token|auth_token)\b
        \s*[:=]\s*["']([A-Za-z0-9_\-\.+/]{12,})["']"""
)

WORD_RE = re.compile(r"[A-Za-z0-9_\-]{25,}")

# Checked-in allowlist: (file-relative-path, matched literal or "<any>") -> reason.
# Only add entries here with a justification in docs/conventions/security.md.
ALLOWLIST: dict[tuple[str, str], str] = {
    ("tests/test_convention_checkers.py", "sk-" + "PLANTEDFAKEKEY1234567890abcd"): (
        "deliberate planted-key self-test fixture; not a real credential"
    ),
}


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {c: s.count(c) for c in set(s)}
    return -sum((n / len(s)) * math.log2(n / len(s)) for n in freq.values())


def check_matrix(repo_root: Path) -> list[str]:
    violations: list[str] = []
    matrix = repo_root / MATRIX_PATH
    if not matrix.is_file():
        return [f"E1 {MATRIX_PATH}: matrix file missing"]
    with matrix.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return [f"E1 {MATRIX_PATH}: matrix is empty"]
    header = rows[0]
    if header != EXPECTED_COLUMNS:
        violations.append(
            f"E1 {MATRIX_PATH}: header mismatch; expected {EXPECTED_COLUMNS}, got {header}"
        )
        return violations
    for i, row in enumerate(rows[1:], start=2):
        if len(row) != len(EXPECTED_COLUMNS):
            violations.append(f"E1 {MATRIX_PATH}:{i}: {len(row)} columns, expected 10")
            continue
        status = row[9].strip().lower()
        if status not in ALLOWED_STATUSES:
            violations.append(f"E2 {MATRIX_PATH}:{i}: status '{row[9]}' not in {sorted(ALLOWED_STATUSES)}")
            continue
        if status == "verified":
            for col_idx, col in ((6, "implementation_location"), (7, "test_location"), (8, "evidence_artifact")):
                value = row[col_idx].strip()
                if not value:
                    continue
                # multi-path cells separated by " + "
                for part in value.split("+"):
                    part = part.strip()
                    if not part:
                        continue
                    if not (repo_root / part).exists():
                        violations.append(
                            f"E3 {MATRIX_PATH}:{i}: verified row references missing {col} '{part}'"
                        )
    return violations


def check_evidence_locations(repo_root: Path) -> list[str]:
    """E4: evidence-looking files must live under evidence/."""
    violations: list[str] = []
    evidence_name = re.compile(r"(result|metrics|experiment|audit)[_-]", re.IGNORECASE)
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()
        parts = rel.split("/")
        if parts[0] in {"evidence", ".git", ".claude", "openspec", "report"} or parts[0].startswith("case") and "outputs" in parts:
            continue
        if path.suffix.lower() in {".json", ".csv", ".txt"} and evidence_name.search(path.stem):
            violations.append(f"E4 {rel}: evidence-looking file outside evidence/ (rename or move)")
    return violations


def allowed(rel: str, literal: str) -> bool:
    return (rel, literal) in ALLOWLIST or (rel, "<any>") in ALLOWLIST


def scan_secrets(repo_root: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        rel = path.relative_to(repo_root).as_posix()
        if any(part in SCAN_SKIP_DIRS for part in Path(rel).parts[:-1]):
            continue
        if rel.startswith("evidence/security_test_results") and "planted" in path.stem:
            continue  # dedicated planted-fixture files used by our own tests
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for regex, label in SECRET_PATTERNS:
            for m in regex.finditer(text):
                if not allowed(rel, m.group(0)):
                    violations.append(f"S1 {rel}: {label} '{m.group(0)[:12]}...'")
        for m in ASSIGNMENT_RE.finditer(text):
            literal = m.group(1)
            if not allowed(rel, literal):
                violations.append(f"S1 {rel}: hardcoded credential assignment '{m.group(0)[:40]}...'")
        for m in WORD_RE.finditer(text):
            token = m.group(0)
            if shannon_entropy(token) > 4.5 and not allowed(rel, token):
                violations.append(f"S1 {rel}: high-entropy string '{token[:16]}...'")
    return violations


def run_check(repo_root: Path = REPO_ROOT) -> list[str]:
    return check_matrix(repo_root) + check_evidence_locations(repo_root) + scan_secrets(repo_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--skip-secrets", action="store_true", help="skip S1 secret scan")
    args = parser.parse_args(argv)
    violations: list[str] = []
    violations.extend(check_matrix(args.root))
    violations.extend(check_evidence_locations(args.root))
    if not args.skip_secrets:
        violations.extend(scan_secrets(args.root))
    if violations:
        print(f"EVIDENCE/SECURITY CONVENTION VIOLATIONS ({len(violations)}):")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("Evidence and security conventions OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
