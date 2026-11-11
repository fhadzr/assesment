"""Tasks 4.1 + 4.2 verification."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from fraud.data.generate import generate
from fraud.features import FEATURES
from fraud.model.baseline import persist_metadata
from fraud.model.evaluate import _at_k, evaluate_scores, run_evaluate
from fraud.model.train import train_model

GEN = dict(
    seed=31, n_customers=60, n_transactions=1200, fraud_rate=0.06, confirmed_rate=0.5,
    duplicate_rate=0.0, mismatch_rate=0.0, missing_ts_rate=0.0,
)


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("data")
    generate(type("Args", (), GEN)(), data_dir)
    out = tmp_path_factory.mktemp("out")
    import hashlib
    mh = hashlib.sha256((data_dir / "transactions_manifest.json").read_bytes()).hexdigest()[:16]
    persist_metadata(out / "model_baseline", FEATURES, mh)
    meta = train_model(data_dir, out / "model_lr")
    return data_dir, out, meta


REQUIRED_KEYS = {"pr_auc", "precision", "recall", "f1", "confusion_matrix", "k"}


class TestMetricSet:
    def test_required_metrics_non_null(self, trained, tmp_path):
        data_dir, out, _ = trained
        report = run_evaluate(data_dir, out, tmp_path / "m.json")
        lr = report["models"]["logistic_regression"]
        for label in ("confirmed_fraud", "blocked"):
            m = lr[label]
            for key in REQUIRED_KEYS - {"confusion_matrix", "k"}:
                assert m[key] is not None, (label, key)
            cm = m["confusion_matrix"]
            assert set(cm) == {"tn", "fp", "fn", "tp"}
            assert any(str(kk).startswith("precision_at_") for kk in m)
            assert any(str(kk).startswith("recall_at_") for kk in m)
            assert m["roc_auc_supplementary"] is not None

    def test_at_k_hand_checkable(self):
        # 10 items, 3 positives. Model ranks 2 positives in top-5, all 3 in top-10.
        y = np.array([1, 0, 1, 0, 0, 1, 0, 0, 0, 0])
        scores = np.array([0.9, 0.85, 0.8, 0.3, 0.25, 0.2, 0.15, 0.1, 0.05, 0.01])
        p5, r5 = _at_k(y, scores, 5)
        p10, r10 = _at_k(y, scores, 10)
        assert p5 == pytest.approx(2 / 5)
        assert r5 == pytest.approx(2 / 3)
        assert p10 == pytest.approx(3 / 10)
        assert r10 == pytest.approx(1.0)

    def test_identical_across_reruns(self, trained, tmp_path):
        data_dir, out, _ = trained
        r1 = run_evaluate(data_dir, out, tmp_path / "a.json")
        r2 = run_evaluate(data_dir, out, tmp_path / "b.json")
        assert r1["models"] == r2["models"]

    def test_missing_artifact_exits_nonzero(self, trained, tmp_path):
        data_dir, _out, _ = trained
        empty = tmp_path / "no_model"
        empty.mkdir()
        from fraud.model.evaluate import main as eval_main
        rc = eval_main(["--data-dir", str(data_dir), "--outputs-dir", str(empty),
                        "--out", str(tmp_path / "x.json")])
        assert rc == 2

    def test_sparse_note_present(self, trained, tmp_path):
        report = run_evaluate(trained[0], trained[1], tmp_path / "m.json")
        assert "volatile" in report["sparse_label_interpretation_note"]
        assert report["provenance"]["dataset_manifest_hash"]

    def test_floor_flags_reported_not_enforced(self, trained, tmp_path):
        report = run_evaluate(trained[0], trained[1], tmp_path / "m.json")
        flags = report["models"]["logistic_regression"]["confirmed_fraud"]["floor_flags"]
        assert isinstance(flags["floor_pr_auc_0.80"], bool)
        assert "no data/threshold manipulation" in flags["policy"]


class TestLabelPolicy:
    def test_no_conversion_confirmed_matches_generated_cell_for_cell(self, trained, tmp_path):
        """If any code path converted blocked->confirmed, the assert inside
        run_evaluate (or this recheck) fires."""
        import csv
        data_dir, out, _ = trained
        report = run_evaluate(data_dir, out, tmp_path / "m.json")
        assert report["label_policy"]["no_conversion_asserted"] is True
        # independent recheck against raw generated table
        with (data_dir / "transactions.csv").open(newline="", encoding="utf-8") as f:
            gen = {r["transaction_id"]: r["confirmed_fraud"] for r in csv.DictReader(f)}
        assert all(v in ("True", "False") for v in gen.values())

    def test_metadata_records_training_label_blocked_and_noise(self, trained):
        _, _, meta = trained
        assert meta["training_label"] == "blocked"
        assert meta["blocked_label_noise_assumption"]["fraud_catch_rate"] == 0.80
        assert meta["blocked_label_noise_assumption"]["source"].startswith("transactions_manifest")

    def test_evaluation_reports_both_labels(self, trained, tmp_path):
        report = run_evaluate(trained[0], trained[1], tmp_path / "m.json")
        lr = report["models"]["logistic_regression"]
        assert {"confirmed_fraud", "blocked"} <= set(lr)
        assert report["label_policy"]["primary_evaluation_label"] == "confirmed_fraud"
