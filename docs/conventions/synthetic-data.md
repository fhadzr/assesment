# Synthetic Data Conventions

All datasets in this repository are synthetic, seeded, and reproducible. These conventions are enforced by `scripts/check_data_conventions.py` (`make check-data`); violating files fail the check with a rule ID.

## The generator contract

Every dataset under a case's data directories is produced by a checked-in generator:

| Data location | Generator location |
| --- | --- |
| `case1_fraud/data/` | `case1_fraud/src/generate*.py` or `case1_fraud/scripts/generate*.py` |
| `case2_docintel/samples/`, `case2_docintel/expected/` | `case2_docintel/src/generate*.py` or `case2_docintel/scripts/generate*.py` |
| `case3_rag/data/` | `case3_rag/src/generate*.py` or `case3_rag/scripts/generate*.py` |

A generator module is any file matching `generate*.py` or `*generator.py` under the case's `src/` or `scripts/`.

Rules the checker enforces:

- **R1 — generated, never hand-authored**: a data file with no generator in its case is a violation. Regenerating with the recorded seed must reproduce the file byte-identically ( generators must avoid sources of nondeterminism such as set iteration order or unseeded randomness).
- **R2 — seedable**: every generator must accept a `--seed` argument (defaulting to a documented constant). The checker statically requires the generator source to reference a seed.
- **R3 — no real PII**: data files must not contain SSN-like patterns or Luhn-valid card-like numbers. Person/account fields must be fabricated by the generator's RNG.

## Seeds and manifests

The default seed of each generator must be recorded where the data is consumed — simplest is a `seed.txt` or `manifest.json` next to the outputs (both are exempt from the "generated data" gitignore rules and are tracked):

```json
{
  "generator": "case1_fraud/src/generate_transactions.py",
  "seed": 42,
  "generated_at_utc": "2026-11-11T00:00:00Z"
}
```

`seed.txt`/`manifest.json`/`schema.json`/`.gitkeep` are the only files the data-convention checker never treats as data.

## Schema documentation

Each generator must document its output schema — field names, types, meaning — either in its module docstring or in a sibling `schema.json`. Consumers must not reverse-engineer fields from data.

## Running the check

```bash
make check-data                       # via make
python scripts/check_data_conventions.py   # direct
```

Exit code 0 = conventions hold. Exit 1 prints each violation with its rule ID.
