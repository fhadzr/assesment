"""Chronological train/validation/test split (task 2.2).

Splits transactions by timestamp quantile cut points (default 70/15/15).
Strict ordering: max(train ts) < min(val ts) < max(val ts) < min(test ts).
Writes outputs/split_summary.json with boundaries, counts, label prevalence.
Deterministic for the same data + proportions.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

SPLIT_VERSION = "1.0.0"
LABELS = ("ground_truth_fraud", "confirmed_fraud", "blocked")


def _load_transactions(data_dir: Path) -> list[dict]:
    with (data_dir / "transactions.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: r["ts"])  # stable chronological order
    return rows


def _clean_exact_duplicates(rows: list[dict]) -> tuple[list[dict], int]:
    seen: set[tuple] = set()
    kept: list[dict] = []
    removed = 0
    for r in rows:
        key = tuple(sorted(r.items()))
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        kept.append(r)
    return kept, removed


def split_transactions(rows: list[dict], train_frac: float = 0.70, val_frac: float = 0.15) -> dict[str, list[dict]]:
    """Split by timestamp quantiles. Rows carry a synthetic ``_row_id`` index."""
    if not 0 < train_frac < 1 or not 0 < val_frac < 1 or train_frac + val_frac >= 1:
        raise ValueError("proportions must satisfy 0 < train, val and train+val < 1")
    n = len(rows)
    t_cut = rows[int(n * train_frac) - 1]["ts"]
    v_cut = rows[int(n * (train_frac + val_frac)) - 1]["ts"]
    if t_cut == v_cut or rows[0]["ts"] == t_cut:
        raise ValueError(
            "degenerate time range: timestamp quantiles collide; "
            "dataset time span cannot satisfy the configured proportions"
        )
    train = [r for r in rows if r["ts"] <= t_cut]
    val = [r for r in rows if t_cut < r["ts"] <= v_cut]
    test = [r for r in rows if r["ts"] > v_cut]
    if not train or not val or not test:
        raise ValueError("degenerate split: an empty partition resulted")
    if max(r["ts"] for r in train) >= min(r["ts"] for r in val):
        raise ValueError("chronology violated: train/val overlap")
    if max(r["ts"] for r in val) >= min(r["ts"] for r in test):
        raise ValueError("chronology violated: val/test overlap")
    return {"train": train, "validation": val, "test": test}


def build_summary(splits: dict[str, list[dict]], removed_duplicates: int) -> dict:
    def prev(rows: list[dict], label: str) -> float:
        return round(sum(r[label] == "True" for r in rows) / len(rows), 6) if rows else 0.0

    return {
        "split_version": SPLIT_VERSION,
        "proportions": {"train": 0.70, "validation": 0.15, "test": 0.15},
        "boundaries": {
            "train_max_ts": max(r["ts"] for r in splits["train"]),
            "validation_min_ts": min(r["ts"] for r in splits["validation"]),
            "validation_max_ts": max(r["ts"] for r in splits["validation"]),
            "test_min_ts": min(r["ts"] for r in splits["test"]),
        },
        "counts": {name: len(rows) for name, rows in splits.items()},
        "label_prevalence": {
            name: {label: prev(rows, label) for label in LABELS} for name, rows in splits.items()
        },
        "removed_exact_duplicates": removed_duplicates,
    }


def run(data_dir: Path, out_path: Path, train_frac: float = 0.70, val_frac: float = 0.15) -> dict:
    rows = _load_transactions(data_dir)
    rows, removed = _clean_exact_duplicates(rows)
    splits = split_transactions(rows, train_frac, val_frac)
    summary = build_summary(splits, removed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    # persist split assignments for downstream consumers
    for name, part in splits.items():
        ids_path = out_path.parent / f"split_{name}_ids.json"
        ids_path.write_text(json.dumps([r["transaction_id"] for r in part]) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("case1_fraud/data"))
    parser.add_argument("--out", type=Path, default=Path("case1_fraud/outputs/split_summary.json"))
    args = parser.parse_args(argv)
    try:
        summary = run(args.data_dir, args.out)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {args.out}: counts {summary['counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
