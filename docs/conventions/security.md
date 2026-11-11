# Security Conventions

## Secrets

- **No secrets in source code.** Credentials come from environment variables (e.g. `os.environ["GROQ_API_KEY"]`), never literals, never `.env` files that are tracked. `.gitignore` excludes `.env`/`*.env`/`.key`/`.pem`.
- The automated secret scan (rule S1 of `make check-evidence`) flags key-shaped tokens (`sk-`/`gsk_`/`AKIA`/`ghp_`/`xox`-prefixed), credential-shaped assignments (`api_key = "..."`, `password =`, `secret =`, `token =` with literal values), and high-entropy strings in tracked source files.
- **Allowlist process**: a genuine false positive is added to `ALLOWLIST` in `scripts/check_evidence_conventions.py` with the matched literal and a one-line reason, and the reason must be recorded here. Current entries:
  - `tests/test_convention_checkers.py` — planted fake key `sk-PLANTEDFAKE...` used to prove the scanner flags real leaks; it is not a credential.

## PII

- Synthetic data must contain no real PII (enforced by `make check-data`, rule R3).
- **No PII in logs**: logging configuration is case-level scope. When a case introduces logging, its design must show that person-identifying fields are excluded or redacted from log output, and its security tests must assert it.

## Access control and LLM context

- **Access control is applied before LLM context construction** — filter what reaches the model, not just what returns to the user. This is Case 3 scope; its spec and tests own the requirement. The foundation only records the ordering rule so later designs inherit it.

## Confidential data transmission

- Never transmit confidential data without authorization. Automated tests use mock LLM providers exclusively (no real provider calls), so the test suite is offline-safe and transmits nothing.

## Security tests

Every case must include security tests; their outputs land in `evidence/security_test_results/`. The foundation-level scan (`make check-evidence`) is the cross-case floor until case-level tests exist.
