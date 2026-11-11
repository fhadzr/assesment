#!/usr/bin/env python
"""Create a case venv and install the case editable + pinned requirements.

Usage: python scripts/setup_case.py <case-dir>

Idempotent: reuses an existing venv. Shell-free so the Makefile stays
portable across POSIX and Windows (no interpreter-path branching in make).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def venv_python(case_dir: Path) -> Path:
    scripts = case_dir / ".venv" / "Scripts" / "python.exe"
    posix = case_dir / ".venv" / "bin" / "python"
    return scripts if scripts.exists() else posix


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    case_dir = REPO_ROOT / argv[0]
    if not (case_dir / "pyproject.toml").is_file():
        print(f"error: {case_dir} has no pyproject.toml")
        return 2

    if venv_python(case_dir).exists():
        print(f"{case_dir.name}: venv exists, reusing")
    else:
        print(f"{case_dir.name}: creating venv")
        subprocess.run([sys.executable, "-m", "venv", str(case_dir / ".venv")], check=True)

    py = str(venv_python(case_dir))
    subprocess.run([py, "-m", "pip", "install", "--upgrade", "pip", "-q"], check=True)
    subprocess.run(
        [py, "-m", "pip", "install", "-q", "-e", str(case_dir), "-r", str(case_dir / "requirements.txt")],
        check=True,
    )
    print(f"{case_dir.name}: ready")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
