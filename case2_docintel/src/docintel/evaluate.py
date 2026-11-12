"""Executable evaluation (task 5.1) — honest numbers only.

Per-field accuracy vs expected JSON, missing rate, error breakdown, per-doc
latency, and tokens/cost strictly from provider response metadata:
  - mock:  tokens=0 cost=0, basis "mock-zero-by-construction"
  - real:  tokens/cost from response usage; if no usage metadata -> null,
           basis "metadata-unavailable" (never zero, never estimated).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from docintel.core import extract_document
from docintel.corpus.schema import FIELD_NAMES
from docintel.providers import make_provider


def evaluate(corpus_dir: Path, provider_name: str = "mock", model: str | None = None) -> dict:
    samples = corpus_dir / "samples"
    expected_dir = corpus_dir / "expected"
    if not samples.is_dir() or not any(samples.glob("*.pdf")):
        raise FileNotFoundError(f"corpus missing under {corpus_dir} (expected samples/*.pdf)")

    provider = make_provider(provider_name) if model is None else make_provider(provider_name, model=model)

    per_field = {f: {"correct": 0, "total": 0} for f in FIELD_NAMES}
    missing = {f: 0 for f in FIELD_NAMES}
    error_breakdown: dict[str, int] = {}
    latencies_ms: list[int] = []
    usage_accum: dict = {"tokens": 0, "cost": 0.0, "basis": None, "provider": provider_name, "model": model}

    pdf_files = sorted(samples.glob("*.pdf"))
    for pdf in pdf_files:
        expected = json.loads((expected_dir / (pdf.stem + ".json")).read_text())
        t0 = time.perf_counter()
        result = extract_document(pdf.name, pdf.read_bytes(), provider)
        latencies_ms.append(int((time.perf_counter() - t0) * 1000))

        error_breakdown[result.status] = error_breakdown.get(result.status, 0) + 1
        for f in FIELD_NAMES:
            per_field[f]["total"] += 1
            if result.fields.get(f) == expected.get(f):
                per_field[f]["correct"] += 1
            elif result.fields.get(f) in (None, ""):
                missing[f] += 1

        usage_accum["basis"] = result.usage.get("cost_basis")
        if result.usage.get("tokens") is not None:
            usage_accum["tokens"] += int(result.usage["tokens"] or 0)
        if result.usage.get("cost") is not None:
            usage_accum["cost"] = round(usage_accum["cost"] + float(result.usage["cost"]), 6)
        elif result.usage.get("cost_basis") == "mock-zero-by-construction":
            pass  # cost stays 0 by construction
        else:
            usage_accum["cost"] = None  # real provider with no metered cost

    field_accuracy = {
        f: round(per_field[f]["correct"] / per_field[f]["total"], 6) if per_field[f]["total"] else None
        for f in FIELD_NAMES
    }
    missing_rate = {
        f: round(missing[f] / per_field[f]["total"], 6) if per_field[f]["total"] else None
        for f in FIELD_NAMES
    }

    return {
        "eval_version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": f"python -m docintel.evaluate --provider {provider_name}" + (f" --model {model}" if model else ""),
        "corpus": {
            "n_documents": len(pdf_files),
            "path": str(corpus_dir),
            "provider_label": provider_name,
        },
        "field_accuracy": field_accuracy,
        "missing_rate": missing_rate,
        "error_breakdown": error_breakdown,
        "latency_ms": {
            "per_document": latencies_ms,
            "mean": round(sum(latencies_ms) / len(latencies_ms), 2) if latencies_ms else None,
        },
        "usage": usage_accum,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path("case2_docintel"))
    parser.add_argument("--provider", default="mock", choices=("mock", "ollama", "groq"))
    parser.add_argument("--model", default=None)
    parser.add_argument("--out", type=Path, default=Path("case2_docintel/outputs/evaluation.json"))
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.corpus, args.provider, args.model)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out} (provider={args.provider}, {report['corpus']['n_documents']} docs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
