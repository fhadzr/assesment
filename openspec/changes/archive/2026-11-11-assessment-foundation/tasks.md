# Tasks

## 1. Version control hygiene

- [x] 1.1 Create root `.gitignore` (venvs, `__pycache__`, `.pytest_cache`, `caseN_*/outputs/*` with `.gitkeep` exceptions, `.env`/`*.env`, secrets patterns, generated data except manifests) and verify `git status` shows no venv/cache entries after a setup+test run
- [x] 1.2 Remove obsolete `.gitkeep` files from directories that now hold real files and verify `git status` remains clean of phantom deletions

## 2. Per-case Python packaging

- [x] 2.1 Create `case1_fraud/pyproject.toml` (setuptools src-layout, package `case1_fraud`, pinned deps in `requirements.txt` — pytest only for now) and verify `pip install -e case1_fraud` succeeds in a fresh venv
- [x] 2.2 Create `case2_docintel/pyproject.toml` + `requirements.txt` (same pattern, package `case2_docintel`) and verify editable install in a fresh venv
- [x] 2.3 Create `case3_rag/pyproject.toml` + `requirements.txt` (same pattern, package `case3_rag`) and verify editable install in a fresh venv
- [x] 2.4 Add each case's minimal package `__init__.py` under `src/` exposing a package docstring/version and verify `python -c "import <pkg>"` succeeds per case venv

## 3. Root pytest configuration and smoke tests

- [x] 3.1 Create root `pytest.ini` (testpaths = three case test dirs, `--import-mode=importlib`, deterministic settings) and verify `pytest --collect-only` lists tests from all three cases
- [x] 3.2 Add `case1_fraud/tests/test_smoke.py` importing `case1_fraud` and asserting its version constant, and verify it passes in the case1 venv
- [x] 3.3 Add `case2_docintel/tests/test_smoke.py` (same pattern) and verify it passes in the case2 venv
- [x] 3.4 Add `case3_rag/tests/test_smoke.py` (same pattern) and verify it passes in the case3 venv

## 4. Convention checker scripts

- [x] 4.1 Implement `scripts/check_data_conventions.py` (stdlib only: every data file has a sibling generator; generators accept `--seed`; no real-PII name patterns) and verify it passes on the empty-data repo and flags a deliberately hand-authored fixture in a self-test
- [x] 4.2 Implement `scripts/check_evidence_conventions.py` (stdlib only: ten-column contract, `pending/verified/failed` statuses, `verified` rows' paths exist, evidence files only under `evidence/`) and verify it passes on the current matrix and flags a corrupted-row fixture in a self-test
- [x] 4.3 Add the secret-pattern scan to the evidence checker (high-entropy strings, key-prefixed tokens, `api_key=` assignments, with documented allowlist) and verify it flags a planted fake key while passing the clean repo
- [x] 4.4 Create `tests/` (root) with pytest tests covering both checkers' pass and fail paths, and verify `pytest tests/` at root passes

## 5. Makefile

- [x] 5.1 Add setup targets (`setup`, `setup-case1..3`) creating per-case venvs with editable installs, shell-portable recipes, and verify `make setup-case1` then `make test-case1` passes end to end
- [x] 5.2 Add test targets (`test` aggregating the three case targets with exit-code aggregation, `test-case1..3`), and verify `make test` passes when all three venvs exist and fails non-zero if any case fails
- [x] 5.3 Add convention targets (`check-data`, `check-evidence`, `check`), wire the checkers, and verify `make check` runs both and passes
- [x] 5.4 Add `clean` (venvs, caches) and verify `make clean && make setup && make test` round-trips

## 6. Documentation

- [x] 6.1 Write `docs/conventions/synthetic-data.md` (generator contract, seed recording, schema documentation, no-real-PII rule, checker usage) and verify each documented command runs as written
- [x] 6.2 Write `docs/conventions/evidence.md` (four evidence locations, matrix columns/status lifecycle, verified-requires-existing-paths rule, checker usage) and verify the documented `make check-evidence` matches the implemented target
- [x] 6.3 Write `docs/conventions/security.md` (secrets posture, secret-scan allowlist process, pointer to case-level PII/access-control responsibilities) and verify it contains no actual credentials
- [x] 6.4 Rewrite README.md with reproducible setup (prerequisites incl. Windows `make` install, `make setup`, `make test`, per-case flows, raw pip/pytest fallback commands, layout table) and verify a fresh-clone simulation follows it successfully
- [x] 6.5 Structure AI_DISCLOSURE.md (usage log table: date, tool, purpose, human review notes) and verify the table renders

## 7. Matrix alignment

- [x] 7.1 Align `evidence/assessment_traceability.csv` with the foundation work (AE rows gain implementation/test/evidence locations; add foundation rows if rubric-mapped) and verify `make check-evidence` passes on the updated matrix
- [x] 7.2 Record the completed foundation artifacts in `evidence/experiment_log/` (setup/verify commands actually run, with outputs) and verify the log entries match executed commands

## 8. Integration verification

- [x] 8.1 Full clean-room verification: fresh venvs, `make setup && make test && make check`, all passing, offline; record exit codes
- [x] 8.2 Verify cross-platform portability of every Makefile target body (no bashisms/PowerShellisms) and document the Windows invocation in README

## Workflow follow-up

- Archive the change after review requirements are satisfied (`openspec archive assessment-foundation`).
- Verify the archived result (main specs gain the four capabilities).
