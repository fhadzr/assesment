"""Rule-based baseline scorer (task 3.1).

Transparent fixed rules, no fitting. Score = weighted sum of normalized rule
fires, clipped to [0,1]. Weights are hand-set from the generator's known
fraud signature (documented in metadata); this is a baseline, not a tuned model.

Rules:
  R1 amount >= 400                       (fraud amounts ~ e^6.2 ≈ 493 mean)
  R2 hour in {0,1,2,3,4,22,23}           (odd hours)
  R3 is_foreign_merchant                 (75% of fraud vs 10% legit)
  R4 amount_z_vs_history >= 3.0          (burst vs own history)
  R5 prior_login_failures_1d >= 2        (credential-stuffing precursor)

score = 0.25*R1 + 0.2*R2 + 0.2*R3 + 0.2*R4 + 0.15*R5
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from fraud.features import FEATURES

BASELINE_VERSION = "1.0.0"

RULES = [
    ("R1_amount_ge_400", 0.25, lambda v: float(v["amount"]) >= 400.0),
    ("R2_odd_hour", 0.20, lambda v: v["hour_of_day"] in {0, 1, 2, 3, 4, 22, 23}),
    ("R3_foreign_merchant", 0.20, lambda v: float(v["is_foreign_merchant"]) >= 1.0),
    ("R4_amount_burst_vs_history", 0.20, lambda v: float(v["amount_z_vs_history"]) >= 3.0),
    ("R5_recent_login_failures", 0.15, lambda v: float(v["prior_login_failures_1d"]) >= 2.0),
]


def score_row(row: dict) -> float:
    total = 0.0
    for _name, weight, predicate in RULES:
        if predicate(row):
            total += weight
    return float(min(total, 1.0))


def score_frame(df) -> np.ndarray:
    """Vectorized over the feature frame (dict-per-row over FEATURES columns)."""
    return np.array([score_row(dict(zip(FEATURES, vals))) for vals in df[FEATURES].to_numpy()])


def persist_metadata(out_dir: Path, feature_list: list[str], dataset_manifest_hash: str) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "model_type": "rule_based_baseline",
        "model_version": BASELINE_VERSION,
        "feature_list": feature_list,
        "rules": [{"name": n, "weight": w} for n, w, _ in RULES],
        "dataset_manifest_hash": dataset_manifest_hash,
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "training_label": None,
        "notes": "fixed transparent rules; no fitting; baseline for comparison",
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def main(argv: list[str] | None = None) -> int:
    import argparse
    import hashlib

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("case1_fraud/data"))
    parser.add_argument("--out", type=Path, default=Path("case1_fraud/outputs/model_baseline"))
    args = parser.parse_args(argv)

    manifest_path = args.data_dir / "transactions_manifest.json"
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()[:16]
    meta = persist_metadata(args.out, FEATURES, manifest_hash)
    print(f"wrote {args.out}/metadata.json (rules: {len(RULES)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
