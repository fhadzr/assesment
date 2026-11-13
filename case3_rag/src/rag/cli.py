"""CLI batch inference (task 4.2) — shares rag.core.ask with the API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rag.core import ask
from rag.retrieval import load_kb


def run_batch(eval_path: Path, kb_path: Path, out_path: Path, provider: str) -> int:
    questions = json.loads(eval_path.read_text(encoding="utf-8"))
    docs = load_kb(kb_path)
    results = []
    for q in questions:
        r = ask(q["question"], q["role"], docs, provider)
        results.append({
            "question": q["question"],
            "role": q["role"],
            "label": q.get("label"),
            "answer": r.answer,
            "citations": r.citations,
            "refusal": r.refusal,
            "hits": [h["doc_id"] for h in r.hits],
            "usage": r.usage,
            "error": r.error,
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path} ({len(results)} questions, provider={provider})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="eval_path", type=Path, required=True)
    parser.add_argument("--kb", dest="kb_path", type=Path, default=Path("case3_rag/data/kb.json"))
    parser.add_argument("--out", dest="out_path", type=Path, required=True)
    parser.add_argument("--provider", default="mock", choices=("mock", "ollama", "groq"))
    args = parser.parse_args(argv)
    return run_batch(args.eval_path, args.kb_path, args.out_path, args.provider)


if __name__ == "__main__":
    sys.exit(main())
