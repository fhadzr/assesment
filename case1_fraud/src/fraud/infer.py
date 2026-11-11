"""CLI batch inference (task 5.4).

CSV in -> CSV out with probability, risk band, reasons, and pseudonymous ids
(auditor role). Shares the Predictor core with the API (equality pinned by
tests). Malformed CSV rejected with row/field-level errors, no partial output.

Usage:
  python -m fraud.infer --in transactions_like.csv --model case1_fraud/outputs/model_lr \
      --out scored.csv --role analyst
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from fraud.features import FEATURES
from fraud.predictor import Predictor
from fraud.pseudonym import pseudonymize

VALID_ROLES = ("analyst", "auditor")


def validate_rows(rows: list[dict]) -> list[str]:
    """Accumulate field-level errors with row numbers; empty list = valid."""
    errors: list[str] = []
    for i, row in enumerate(rows, start=2):  # header is line 1
        for f in FEATURES:
            if f not in row:
                errors.append(f"row {i}: missing required column '{f}'")
                continue
            try:
                float(row[f])
            except (TypeError, ValueError):
                errors.append(f"row {i}: field '{f}' value {row[f]!r} is not numeric")
    return errors


def run_inference(in_csv: Path, model_path: Path, out_csv: Path, role: str) -> int:
    if role not in VALID_ROLES:
        print(f"error: unknown role '{role}'; expected analyst|auditor", file=sys.stderr)
        return 2
    predictor = Predictor(model_path)

    with in_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    missing_cols = [f for f in FEATURES if f not in fieldnames]
    if missing_cols:
        print(f"error: missing required column(s): {missing_cols}", file=sys.stderr)
        return 2

    errors = validate_rows(rows)
    if errors:
        print(f"error: {len(errors)} malformed value(s); refusing to write output:", file=sys.stderr)
        for e in errors[:20]:
            print(f"  {e}", file=sys.stderr)
        return 2

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_fields = ["row_number"]
    if "transaction_id" in fieldnames:
        out_fields.append("transaction_id_pseudonymous" if role == "auditor" else "_")
    out_fields += ["probability", "risk_band", "reasons"]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for i, row in enumerate(rows, start=2):
            feats = {f: float(row[f]) for f in FEATURES}
            result = predictor.predict(feats)
            entry = {
                "row_number": i,
                "probability": result["probability"],
                "risk_band": result["risk_band"],
                "reasons": "; ".join(result["reasons"]),
            }
            if "transaction_id" in fieldnames:
                key = "transaction_id_pseudonymous" if role == "auditor" else "_"
                entry[key] = pseudonymize(row["transaction_id"]) if role == "auditor" else ""
            writer.writerow(entry)
    print(f"wrote {out_csv} ({len(rows)} rows, role={role})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="in_csv", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=Path("case1_fraud/outputs/model_lr"))
    parser.add_argument("--out", dest="out_csv", type=Path, required=True)
    parser.add_argument("--role", choices=VALID_ROLES, default="analyst")
    args = parser.parse_args(argv)
    return run_inference(args.in_csv, args.model, args.out_csv, args.role)


if __name__ == "__main__":
    sys.exit(main())
