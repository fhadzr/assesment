"""Task 1.2 verification: determinism, manifests, invalid args."""

from __future__ import annotations

import filecmp
import json
from pathlib import Path

import pytest

from fraud.data.generate import generate, main

DEFAULTS = dict(
    seed=42, n_customers=50, n_transactions=500, fraud_rate=0.05,
    confirmed_rate=0.5, duplicate_rate=0.02, mismatch_rate=0.01, missing_ts_rate=0.01,
)


def _gen(tmp_path: Path, **overrides) -> Path:
    ns = type("Args", (), {**DEFAULTS, **overrides})()
    out = tmp_path / "data"
    generate(ns, out)
    return out


def _rows(path: Path, name: str) -> list[dict]:
    import csv
    with (path / f"{name}.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_deterministic_regeneration(tmp_path):
    a = _gen(tmp_path / "a")
    b = _gen(tmp_path / "b")
    for name in ("customers", "transactions", "devices", "logins"):
        assert filecmp.cmp(a / f"{name}.csv", b / f"{name}.csv", shallow=False), name


def test_different_seed_differs(tmp_path):
    a = _gen(tmp_path / "a", seed=42)
    b = _gen(tmp_path / "b", seed=1337)
    ra = {r["transaction_id"]: r for r in _rows(a, "transactions")}
    rb = {r["transaction_id"]: r for r in _rows(b, "transactions")}
    diffs = [k for k in ra if k in rb and ra[k] != rb[k]]
    assert diffs, "same ids but identical content across seeds is suspicious"


def test_manifest_contents(tmp_path):
    out = _gen(tmp_path)
    m = json.loads((out / "transactions_manifest.json").read_text())
    assert m["seed"] == 42
    assert m["rows"] == len(_rows(out, "transactions"))
    assert m["generator_version"]
    assert m["generated_at_utc"].endswith("Z")
    assert set(m["label_prevalence"]) == {"ground_truth_fraud", "confirmed_fraud", "blocked"}
    assert m["defects_injected"]["duplicate_transactions"] > 0
    for other in ("customers", "devices", "logins"):
        om = json.loads((out / f"{other}_manifest.json").read_text())
        assert om["seed"] == 42 and om["rows"] == len(_rows(out, other))


@pytest.mark.parametrize("bad", [
    dict(n_transactions=0),
    dict(fraud_rate=1.5),
    dict(confirmed_rate=0.9),
    dict(duplicate_rate=1.5),
    dict(mismatch_rate=1.0),
])
def test_invalid_arguments_exit_nonzero(tmp_path, bad):
    out = tmp_path / "noout"
    ns = type("Args", (), {**DEFAULTS, **bad})()
    with pytest.raises(ValueError):
        generate(ns, out)
    assert not out.exists(), "validation must fail before writing any file"


def test_cli_invalid_seed_rejected(capsys):
    import pytest as _pytest

    with _pytest.raises(SystemExit) as excinfo:
        main(["--seed", "not_an_int", "--out", "unused"])
    assert excinfo.value.code != 0
