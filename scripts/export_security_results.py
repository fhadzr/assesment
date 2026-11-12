#!/usr/bin/env python
"""Export per-case security-test results to evidence JSON (case1 + case2).

Runs the given case's security suite with pytest's JUnit-XML report and
converts it to evidence/security_test_results/<case>_security.json, listing
each test (assertion group) with pass/fail. Evidence is a test artifact.

Usage: python scripts/export_security_results.py [case1_fraud|case2_docintel]
"""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES = {"case1_fraud", "case2_docintel"}
PREFIX = {"case1_fraud": "case1", "case2_docintel": "case2", "case3_rag": "case3"}


def main(argv: list[str] | None = None) -> int:
    case_name = (argv or ["case1_fraud"])[0]
    if case_name not in CASES:
        print(f"error: unknown case '{case_name}'; valid: {sorted(CASES)}", file=sys.stderr)
        return 2

    case = REPO_ROOT / case_name
    out = REPO_ROOT / "evidence" / "security_test_results" / f"{PREFIX[case_name]}_security.json"
    xml_path = case / "outputs" / "security_junit.xml"
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    pytest_exe = case / ".venv" / "Scripts" / "pytest.exe"
    if not pytest_exe.exists():
        pytest_exe = case / ".venv" / "bin" / "pytest"

    cmd = [str(pytest_exe), str(case / "tests" / "test_security.py"), f"--junitxml={xml_path}", "-q"]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    print(proc.stdout.strip()[-600:])

    root = ET.parse(xml_path).getroot()
    suite = root.find("testsuite")
    tests = []
    for tc in suite.findall("testcase"):
        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")
        if failure is not None or error is not None:
            status = "fail"
            detail = (failure.get("message") if failure is not None else "") or (error.get("message") if error is not None else "")
        elif skipped is not None:
            status = "skipped"
            detail = skipped.get("message") or ""
        else:
            status = "pass"
            detail = ""
        tests.append({"test": tc.get("name"), "class": tc.get("classname", ""), "status": status, "detail": detail[:300]})

    report = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_suite": f"{case_name}/tests/test_security.py",
        "command": f"python scripts/export_security_results.py {case_name}",
        "summary": {
            "total": suite.get("tests"),
            "failures": suite.get("failures"),
            "errors": suite.get("errors"),
            "skipped": suite.get("skipped"),
            "exit_code": proc.returncode,
        },
        "assertions": tests,
        "surfaces": ["fastapi_api", "cli"],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(tests)} assertions, exit={proc.returncode})")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
