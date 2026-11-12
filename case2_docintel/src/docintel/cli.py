"""CLI batch extraction (task 3.2) — shares docintel.core with the API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from docintel.core import extract_document
from docintel.providers import make_provider

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


def run_batch(in_path: Path, out_path: Path, provider_name: str) -> int:
    files = (
        sorted(p for p in in_path.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES)
        if in_path.is_dir()
        else [in_path]
    )
    if not files:
        print(f"error: no supported documents found under {in_path}", file=sys.stderr)
        return 2

    provider = make_provider(provider_name)
    results = []
    for f in files:
        result = extract_document(f.name, f.read_bytes(), provider)
        results.append({
            "document_id": result.document_id,
            "status": result.status,
            "fields": result.fields,
            "field_statuses": result.field_statuses,
            "review": [vars(e) for e in result.review],
            "usage": result.usage,
            "error": result.error,
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path} ({len(results)} documents, provider={provider_name})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="in_path", type=Path, required=True)
    parser.add_argument("--out", dest="out_path", type=Path, required=True)
    parser.add_argument("--provider", default="mock", choices=("mock", "ollama", "groq"))
    args = parser.parse_args(argv)
    return run_batch(args.in_path, args.out_path, args.provider)


if __name__ == "__main__":
    sys.exit(main())
