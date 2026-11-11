#!/usr/bin/env python
"""Export case1 security-test results to evidence JSON (task 6.3).

Runs the case1 security suite with pytest's JUnit-XML report and converts it
to evidence/security_test_results/case1_security.json, listing each test
(assertion group) with pass/fail. Evidence is a test artifact, not prose.

Usage: python scripts/export_security_results.py
"""

from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CASE = REPO_ROOT / "case1_fraud"
OUT = REPO_ROOT / "evidence" / "security_test_results" / "case1_security.json"


def main() -> int:
    xml_path = CASE / "outputs" / "security_junit.xml"
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    pytest_exe = CASE / ".venv" / "Scripts" / "pytest.exe"
    if not pytest_exe.exists():
        pytest_exe = CASE / ".venv" / "bin" / "pytest"
    cmd = [
        str(pytest_exe), str(CASE / "tests" / "test_security.py"),
        f"--junitxml={xml_path}", "-q",
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    print(proc.stdout.strip()[-500:])

    root = ET.parse(xml_path).getroot()
    suite = root.find("testsuite")
    tests = []
    for case in suite.findall("testcase"):
        name = case.get("name")
        classname = case.get("classname", "")
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        if failure is not None or error is not None:
            status = "fail"
            detail = (failure is not None and failure.get("message") or "") or (error is not None and error.get("message") or "")
        elif skipped is not None:
            status = "skipped"
            detail = skipped.get("message") or ""
        else:
            status = "pass"
            detail = ""
        tests.append({"test": name, "class": classname, "status": status, "detail": detail[:300]})

    report = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_suite": "case1_fraud/tests/test_security.py",
        "command": "python scripts/export_security_results.py",
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(__import__("json").dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(tests)} assertions, exit={proc.returncode})")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
