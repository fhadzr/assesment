# Spec Delta

## Purpose

Gives the repository a root pytest configuration and deterministic test discovery so every case's tests run together or individually, offline, with a single command.

## ADDED Requirements

### Requirement: Root pytest configuration
The repository root SHALL carry a pytest configuration that discovers tests from all three case `tests/` directories by default and sets deterministic options: no network access required, no random ordering, no timeouts dependent on external services.

#### Scenario: Single command runs all case tests
- **WHEN** the root pytest command or `make test` runs on a machine with no internet connection
- **THEN** tests from `case1_fraud/tests`, `case2_docintel/tests`, and `case3_rag/tests` are all collected and pass without network access

#### Scenario: No tests collected fails loudly
- **WHEN** pytest is pointed at a path containing no test files
- **THEN** it exits non-zero with "no tests ran" rather than exiting zero silently

### Requirement: Per-case test selection
Running a single case's tests SHALL require only that case's directory as the argument or its dedicated Makefile target, without editing configuration.

#### Scenario: Single case selection
- **WHEN** `make test-case1` (or the equivalent pytest path argument for `case1_fraud/tests`) runs
- **THEN** only case1 tests are collected and executed

### Requirement: Smoke tests prove the harness
Each case's `tests/` directory SHALL contain at least one trivially passing test that imports the case's own package, demonstrating that discovery, imports, and the per-case environment work end to end.

#### Scenario: Fresh clone passes after setup
- **WHEN** the repository is cloned, setup targets are run, and the full test target is executed
- **THEN** at least one test per case passes and the overall exit code is zero

#### Scenario: Harness failure is diagnosable
- **WHEN** a case's package is broken (for example its `src/` layout is corrupted)
- **THEN** that case's smoke test fails with an import error naming the case package, rather than being silently skipped

### Requirement: Tests must not depend on external services
No automated test SHALL call a real LLM provider, external API, or network resource; any test needing a provider SHALL use a mock or deterministic local substitute.

#### Scenario: Offline test run
- **WHEN** the entire test suite runs with network access disabled
- **THEN** all tests pass

#### Scenario: Test attempting a real provider call fails the suite
- **WHEN** a test is written to call a real external provider and the suite runs offline
- **THEN** the suite fails rather than reporting a pass based on a fabricated response
