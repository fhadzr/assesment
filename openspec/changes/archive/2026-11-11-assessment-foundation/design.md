# Design

## Context

The repo has only a directory skeleton (gitkeep'd case/evidence/report dirs, placeholder README/AI_DISCLOSURE, a Makefile with one `help` target, and a 47-row traceability CSV with all statuses `pending`). No Python packaging, no pytest config, no `.gitignore`. Windows is the primary development platform (PowerShell + Git Bash), which constrains Makefile and setup-script choices. The assessment forbids fabricated metrics and requires synthetic data and reproducible setup — the foundation must make those constraints easy to obey, not merely document them.

See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- A developer (or assessor) can go from fresh clone → running all tests in one documented command sequence, offline.
- Each case is an independently installable, independently testable unit with pinned dependencies.
- Data and evidence conventions are enforced by checks, not just described in docs.
- Everything works on Windows-first without breaking Unix.

**Non-Goals:**
- Any prototype functionality (models, APIs, extraction, RAG) — later changes.
- CI pipelines, containers, or pre-commit hooks — can be added later without touching these specs.
- A shared library extracting common code across cases — premature until duplication actually appears.

## Decisions

### D1: Per-case `pyproject.toml` (src-layout) over one root package
Each case gets `caseN_*/pyproject.toml` with setuptools src-layout (`src/<case_pkg>/`) and its own pinned `requirements.txt`. Alternatives: a single root `pyproject.toml` (rejected: one dependency set means version conflicts between cases — e.g. case 3's vector-store pin breaking case 1's sklearn pin — violating the isolation acceptance criterion) or a uv workspace (rejected: adds a non-standard tool requirement for the assessor; pip+venv is universally available).

Root gets **no** installable package — only `pytest.ini` and tooling, so the root can never accumulate accidental shared code.

### D2: pip + venv per case; `pip install -e <case>` for tests
`make setup` (or `make setup-case1`) creates `caseN_*/.venv` and pip-installs that case in editable mode plus its pinned requirements. Alternatives: a single shared venv with all deps (rejected — same conflict problem), conda (heavier, less universal), Poetry/PDM (extra tooling). Tests run via the case's own venv: `case1_fraud/.venv/Scripts/python -m pytest` (Windows) with a Make variable abstracting the interpreter path so the same target works on Unix (`bin/python`).

### D3: Root `pytest.ini` for discovery; each case runs in its own venv
`pytest.ini` at root sets `testpaths = case1_fraud/tests case2_docintel/tests case3_rag/tests`, `-p no:cacheprovider` alternatives evaluated below. But a single root pytest run needs one interpreter; per-case venvs mean **`make test` loops the three case targets and aggregates exit codes** rather than invoking one root pytest process. `pytest.ini` still exists so a bare `pytest` from any case directory does sane discovery; `--import-mode=importlib` keeps the three same-named `tests` packages from colliding. Alternatives: tox/nox orchestrating envs (rejected for now — heavier than the assessment needs; can be added later without spec change).

### D4: Determinism-first pytest settings
Settings: `testpaths` as above, `--import-mode=importlib`, `-p no:randomly` (defensive), strict markers, `filterwarnings = error` deferred (too aggressive while cases are empty — revisit when cases land). Offline determinism is a spec scenario, so no plugins requiring network.

### D5: Synthetic-data convention = a checked-in contract + a checker script
Conventions documented in `docs/conventions/synthetic-data.md`; enforcement via `scripts/check_data_conventions.py` (pure stdlib): for every data file under a case's data dirs there must be a sibling generator module under `src/`, and every generator must accept `--seed` with a recorded default emitted into a `seed.txt`/manifest next to outputs. The checker is wired as a Make target (`make check-data`) and a root-level pytest test, so it runs with `make test` — the convention is executable, not aspirational. Alternative: pre-commit hook only (rejected: hooks aren't run by assessors; tests are).

### D6: Evidence conventions = documented layout + same checker
`docs/conventions/evidence.md` documents the four evidence locations, the ten-column matrix contract, the `pending/verified/failed` status lifecycle, and the rule that `verified` requires existing paths + passing tests. `scripts/check_evidence_conventions.py` validates the CSV (columns, statuses, and that any `verified` row's paths exist) and flags evidence-looking files outside `evidence/`. Wired into `make check-evidence` and the root test suite.

### D7: Makefile as the single entry point
Targets: `help`, `setup`, `setup-case1..3`, `test`, `test-case1..3`, `check-data`, `check-evidence`, `check` (data+evidence), `clean`. Shell-portable recipe bodies (no bashisms), `PYTHON ?=` overridable variable; on Windows, Git Bash (`make` via choco/scoop or `mingw32-make`) is the documented prerequisite — acceptable because the assessment's own tech list already assumes a dev toolchain. Alternative: justfile/taskfile (nicer but non-standard); PowerShell entry script (Unix-hostile). If `make` is genuinely unavailable, every recipe's underlying command is printed in README so steps remain reproducible without it.

### D8: `.gitignore` covers venvs, caches, outputs — with outputs split
`outputs/` contents are generated (ignore them), but each case's `outputs/` needs `.gitkeep`-style tracking plus the data/evidence conventions mean *some* outputs (evidence CSVs, evaluation JSONs referenced by the matrix) must be committable. Decision: ignore `caseN_*/outputs/*` by default; evidence and committed outputs live under `evidence/` (never ignored) per the evidence spec, so "actual outputs exist" (definition of done) is satisfied by evidence copies, not by case output dirs. This keeps the repo clean while preserving the audit trail.

### D9: Privacy and security posture at the foundation level
No secrets exist yet; the foundation enforces the posture: `.gitignore` excludes `.env`, `*.env`, `.venv`; the evidence checker (D6) gains a simple secret-pattern scan (high-entropy strings, `sk-`-prefixed tokens, `api_key=` assignments) over tracked source so a leaked key fails `make check` rather than waiting for case-level security tests. Logs: no logging configuration is introduced at foundation level (nothing logs yet); case-level designs own the PII-in-logs requirement. Access-control-before-LLM-context is case-3 scope. Documented in `docs/conventions/security.md`.

### D10: Data flow (foundation level)
```
generator script (seeded, per case)
        │  writes
        ▼
caseN_*/data/ (synthetic only, regenerable, gitignored-except-manifests)
        │  read by
        ▼
caseN_*/src/ (case code, per-case venv)
        │  writes
        ▼
caseN_*/outputs/ (gitignored by default)
        │  copied/promoted when referenced as evidence
        ▼
evidence/ (tracked: matrix, experiment logs, security results, cost analysis)
```
Rule: anything the traceability matrix points at as evidence MUST live under `evidence/` (tracked), so verification (D6 checker) can rely on tracked files.

## Risks / Trade-offs

- [Windows `make` availability] → README documents install (choco/scoop) and prints raw commands for every target; `make` is convenience, not a hard dependency.
- [Three venvs triple setup time and disk] → per-case setup targets make it lazy (set up only the case you're working on); acceptance criterion requires isolation, which costs this.
- [Checker scripts drift from reality / false positives on legitimate files] → checkers are small, stdlib-only, tested by their own pytest tests, and fail open *loudly* (report violation with path and rule) so drift is visible.
- [Secret-scan false positives (e.g. a long hash in test fixtures)] → allowlist mechanism in the checker config with documented justification per entry.
- [`outputs/` gitignored vs "actual outputs exist" definition-of-done] → evidence copies under `evidence/` are the tracked artifact; case README sections state how to regenerate any output.
- [pytest `importlib` mode interacts badly with a future case pattern] → each case's tests import only its own installed package (D1/D2), so collision risk is contained; revisit if a case needs path-hack imports.

## Migration Plan

Greenfield — no existing users or data to migrate. Rollback = delete added files; nothing existing is modified except the placeholder README/AI_DISCLOSURE/Makefile, whose prior content is placeholder-only (recovered from git history if ever needed).

## Open Questions

None blocking — deferrable items are recorded in docs as "revisit" notes (e.g. `filterwarnings = error`, nox/tox adoption).
