# repo-foundation Specification

## Purpose

Defines the repository layout, Python project conventions, per-case dependency isolation, and the executable Makefile workflow commands every V-TEKI case builds on.

## Requirements

### Requirement: Monorepo directory layout
The repository SHALL contain one top-level directory per assessment case (`case1_fraud`, `case2_docintel`, `case3_rag`), each with the subdirectories the case requires, plus shared `scenarios/`, `evidence/`, `report/source/`, and `openspec/` directories. Directory removal or renaming of these top-level names SHALL NOT happen in this change or later ones without an approved OpenSpec change.

#### Scenario: Layout verification
- **WHEN** a fresh clone of the repository is inspected at the root
- **THEN** all four case-specific subdirectories (`case1_fraud/src`, `case1_fraud/tests`, `case2_docintel/src`, `case2_docintel/tests`, `case3_rag/src`, `case3_rag/tests`) and the shared directories (`scenarios/`, `evidence/`, `report/source/`, `openspec/`) exist and are non-empty or git-tracked

#### Scenario: Unknown top-level directory is not silently created
- **WHEN** a case implementation wants a new top-level directory outside the approved set
- **THEN** it SHALL NOT be created ad hoc; the change proposing it must list it in its proposal and be approved first

### Requirement: Per-case Python package layout
Each case's source code SHALL live in an importable Python package under that case's `src/` directory, and that case's tests SHALL live under its `tests/` directory. Case code SHALL NOT import from another case's package.

#### Scenario: Importable per-case packages
- **WHEN** the test suite for any case runs
- **THEN** the case's own package imports succeed without requiring another case's package to be installed

#### Scenario: Cross-case import is rejected
- **WHEN** a test asserts that no case's `src/` imports another case's package (negative test)
- **THEN** no such cross-case import is found

### Requirement: Per-case dependency isolation
Each case SHALL declare its dependencies in its own `requirements.txt`, and setting up a case SHALL create its own virtual environment so that dependencies are installed and version-pinned independently of other cases.

#### Scenario: Isolated environments
- **WHEN** the setup target for case1 is run and then the setup target for case2 is run
- **THEN** two separate virtual environments exist, each containing only its own case's declared dependencies plus shared tooling

#### Scenario: Case runs without another case installed
- **WHEN** a case's test target runs in an environment where the other cases' virtual environments have not been created
- **THEN** the case's tests still pass

### Requirement: Executable Makefile workflow targets
The Makefile SHALL provide targets for environment setup (all cases or one), running all tests, running one case's tests, and cleaning Python caches, and every target SHALL be executable on both Windows and Unix without manual editing.

#### Scenario: Help lists all workflow targets
- **WHEN** `make help` runs
- **THEN** setup, test, per-case test, and clean targets are listed with descriptions

#### Scenario: Unknown target fails
- **WHEN** `make <undefined-target>` runs
- **THEN** make exits non-zero with a "No rule to make target" error rather than silently succeeding

#### Scenario: Cross-platform execution
- **WHEN** any workflow target runs on Windows and on a Unix shell
- **THEN** it completes without shell-specific syntax errors

### Requirement: Version control hygiene
The repository SHALL ignore Python build artifacts, virtual environments, `__pycache__`, pytest caches, and generated case outputs so that generated files are never committed by default.

#### Scenario: Generated artifacts not tracked
- **WHEN** virtual environments are created and tests are run
- **THEN** `git status` reports no virtual-environment directories, `__pycache__`, or `.pytest_cache` entries as untracked additions requiring a decision
