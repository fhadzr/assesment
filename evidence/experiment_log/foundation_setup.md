# Experiment Log — Foundation Setup

## 2026-11-11 · assessment-foundation implementation (Windows 11, Python 3.10.8, MinGW make 4.x)

### Environment

| Item | Value |
| --- | --- |
| OS | Windows 11 (win32) |
| Python | 3.10.8 (`C:\Users\Azhar\AppData\Local\Programs\Python\Python310\python.exe`) |
| make | MinGW `mingw32-make` |
| pytest | 8.3.4 (pinned in each case `requirements.txt`) |

### Commands run and results (recorded during implementation)

| # | Command | Result |
| --- | --- | --- |
| 1 | `python -m venv caseN/.venv` + editable install (×3 cases) | exit 0 — `import fraud/docintel/rag` → `0.1.0` each |
| 2 | `<case>/.venv/Scripts/pytest <case>/tests -q` (×3) | `1 passed` each (smoke tests) |
| 3 | `<case>/.venv/Scripts/pytest tests -q` (root checker tests) | `11 passed` |
| 4 | `python scripts/check_data_conventions.py` | `Data conventions OK`, exit 0 |
| 5 | `python scripts/check_evidence_conventions.py` | `Evidence and security conventions OK`, exit 0 |
| 6 | `mingw32-make help` | lists all targets, exit 0 |
| 7 | `mingw32-make setup` (from clean) | all three cases `ready`, exit 0 |
| 8 | `mingw32-make test` | 3 × `12 passed`, exit 0 |
| 9 | `mingw32-make check` | both checkers OK, exit 0 |
| 10 | `mingw32-make clean` → `setup` → `test` round-trip | exit 0 (re-verified below) |
| 11 | Negative: appended failing test to case2 → `mingw32-make test-case2` | exit 2 (non-zero propagation verified), then restored → exit 0 |

### Reproducing

From a clean checkout (commands as in README):

```bash
make clean
make setup && make test && make check
```

Expected: three case test runs (12 passed each with current test count) and both checkers OK, all exit 0.

**Clean-room re-run after full implementation (2026-11-11):** `make setup` exit 0 · `make test` 3 × `12 passed`, exit 0 · `make check` both OK, exit 0. All 27/27 tasks complete (`openspec status`: all_done).

### Deviations from design

- Design assumed Python ≥3.11; machine has 3.10.8 — all code is 3.10-compatible (`requires-python = ">=3.10"`); no 3.11+ syntax used.
- Case import packages are `fraud`, `docintel`, `rag` (not the case directory names): the directory `case1_fraud/` shadowed an equally-named installed package as a namespace package under pytest. Distinct names fix the collision; specs pin no package name.
- Setup recipes delegate to `scripts/setup_case.py` because make expands recipes before running them, so interpreter-path branching in the recipe evaluated before the venv existed.
