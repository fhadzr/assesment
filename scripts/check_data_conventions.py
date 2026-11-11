#!/usr/bin/env python
"""Check V-TEKI synthetic data conventions (stdlib only).

Rules enforced (see docs/conventions/synthetic-data.md):
  R1: every data file under a case's data directories must be producible by a
      checked-in generator script under that case's src/ (a generator is any
      module named generate*.py or *generator.py, or a script under the case's
      scripts/ dir).
  R2: generators must accept a --seed argument (checked by static text scan for
      "seed").
  R3: no obvious real-PII patterns in data files (SSN-like, credit-card-like
      Luhn-valid numbers) - synthetic generators must fabricate these.

Exit code 0 = conventions hold; 1 = violations found (printed).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# (case directory, data subdirectory) pairs where generated data may live
DATA_DIRS = [
    ("case1_fraud", "data"),
    ("case2_docintel", "samples"),
    ("case2_docintel", "expected"),
    ("case3_rag", "data"),
]

GENERATOR_PATTERNS = ["generate*.py", "*generator.py"]

# Files never treated as data (they are the tracked manifests)
MANIFEST_NAMES = {"manifest.json", "seed.txt", ".gitkeep", "schema.json"}

SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def luhn_valid(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def find_generators(case_dir: Path) -> list[Path]:
    found: list[Path] = []
    src = case_dir / "src"
    scripts = case_dir / "scripts"
    for root in (src, scripts):
        if not root.is_dir():
            continue
        for pattern in GENERATOR_PATTERNS:
            found.extend(root.rglob(pattern))
    return sorted(set(found))


def check_data_file(path: Path, generators: list[Path], repo_root: Path = REPO_ROOT) -> list[str]:
    violations: list[str] = []
    rel = path.relative_to(repo_root)

    # R1: sibling generator must exist for the case
    if not generators:
        violations.append(
            f"R1 {rel}: no checked-in generator script found for this case; "
            f"data must be generated, never hand-authored"
        )

    # R3: no real-PII-looking content (text files only, keep scan cheap)
    if path.suffix.lower() in {".txt", ".csv", ".json", ".jsonl", ".md"}:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        if SSN_RE.search(text):
            violations.append(f"R3 {rel}: SSN-like pattern present in data file")
        for match in re.finditer(r"\b(?:\d[ -]?){13,19}\b", text):
            candidate = match.group(0)
            digits = re.sub(r"\D", "", candidate)
            if 13 <= len(digits) <= 19 and luhn_valid(digits):
                violations.append(
                    f"R3 {rel}: Luhn-valid card-like number {candidate} present"
                )
                break
    return violations


def check_generators(case_dir: Path, generators: list[Path], repo_root: Path = REPO_ROOT) -> list[str]:
    violations: list[str] = []
    for gen in generators:
        rel = gen.relative_to(repo_root)
        try:
            text = gen.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        # R2: must reference a seed parameter
        if not re.search(r"seed", text, re.IGNORECASE):
            violations.append(f"R2 {rel}: generator does not accept/mention a seed")
    return violations


def run_check(repo_root: Path = REPO_ROOT) -> list[str]:
    violations: list[str] = []
    for case_name, data_sub in DATA_DIRS:
        case_dir = repo_root / case_name
        data_dir = case_dir / data_sub
        if not data_dir.is_dir():
            continue
        generators = find_generators(case_dir)
        violations.extend(check_generators(case_dir, generators, repo_root))
        for path in sorted(data_dir.rglob("*")):
            if not path.is_file() or path.name in MANIFEST_NAMES:
                continue
            violations.extend(check_data_file(path, generators, repo_root))
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    violations = run_check(args.root)
    if violations:
        print(f"DATA CONVENTION VIOLATIONS ({len(violations)}):")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("Data conventions OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
