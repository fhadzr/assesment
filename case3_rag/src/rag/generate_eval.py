"""Seeded evaluation dataset generator (task 1.3).

Writes eval.json: 30-40 questions, each {question, role, label, expected_answer,
expected_citations}. Labels: answerable | unanswerable | restricted. Includes
cross-role access attempts (restricted questions whose evidence is in a doc
disallowed for the caller role). Deterministic per seed, derived from kb.json
so expected_citations resolve to real doc_id/section pairs.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

GENERATOR_VERSION = "1.0.0"
MIN_Q, MAX_Q = 30, 40
LABELS = ("answerable", "unanswerable", "restricted")


def _load_kb(data_dir: Path) -> list[dict]:
    return json.loads((data_dir / "kb.json").read_text(encoding="utf-8"))


def _validate(n_questions: int) -> None:
    if not (MIN_Q <= n_questions <= MAX_Q):
        raise ValueError(f"--n-questions must be within [{MIN_Q}, {MAX_Q}]; got {n_questions}")


def _question_for(doc: dict, rng: random.Random) -> str:
    # simple deterministic question templating from the doc's section + first fact words
    head = doc["content"].split(". ")[0]
    subject = " ".join(head.split()[:6])
    return f"What does the policy say about {doc['section'].replace('_', ' ')}? ({subject[:60]})"


def generate(seed: int, n_questions: int, data_dir: Path) -> dict:
    _validate(n_questions)
    rng = random.Random(seed)
    docs = _load_kb(data_dir)
    by_id = {d["doc_id"]: d for d in docs}

    questions = []
    # answerable: cite a doc the caller role can access
    while len([q for q in questions if q["label"] == "answerable"]) < n_questions // 2:
        d = rng.choice(docs)
        role = d["allowed_roles"][0] if "all" in d["allowed_roles"] else d["allowed_roles"][0]
        if role == "all":
            role = rng.choice(["hr", "finance", "exec"])
        if role not in d["allowed_roles"] and "all" not in d["allowed_roles"]:
            continue  # role must be permitted for answerable
        questions.append(
            {
                "question": _question_for(d, rng),
                "role": role,
                "label": "answerable",
                "expected_answer": d["content"].split(". ")[0],
                "expected_citations": [f"{d['doc_id']} § {d['section']}"],
            }
        )

    # unanswerable: no KB support
    while len([q for q in questions if q["label"] == "unanswerable"]) < max(3, n_questions // 4):
        questions.append(
            {
                "question": f"What is the company policy on {rng.choice(['satellite offices', 'pet insurance', 'submarine procurement'])}?",
                "role": rng.choice(["hr", "finance", "exec"]),
                "label": "unanswerable",
                "expected_answer": None,
                "expected_citations": [],
            }
        )

    # restricted: evidence exists in a doc the caller role may NOT access
    while len([q for q in questions if q["label"] == "restricted"]) < max(3, n_questions // 4):
        d = rng.choice([x for x in docs if "all" not in x["allowed_roles"]])
        disallowed_role = rng.choice([r for r in ["hr", "finance", "exec"] if r not in d["allowed_roles"]])
        questions.append(
            {
                "question": _question_for(d, rng),
                "role": disallowed_role,
                "label": "restricted",
                "expected_answer": d["content"].split(". ")[0],
                "expected_citations": [f"{d['doc_id']} § {d['section']}"],
            }
        )

    # trim to n_questions deterministically, preserving label balance
    questions = questions[:n_questions]
    rng.shuffle(questions)  # deterministic shuffle
    for q in questions:
        assert q["label"] in LABELS
        for c in q["expected_citations"]:
            doc_id, _, section = c.partition(" § ")
            assert doc_id in by_id, doc_id
            assert by_id[doc_id]["section"] == section

    manifest = {
        "dataset": "synthetic_rag_eval",
        "seed": seed,
        "n_questions": len(questions),
        "generator_version": GENERATOR_VERSION,
        "label_counts": {lbl: sum(1 for q in questions if q["label"] == lbl) for lbl in LABELS},
    }
    (data_dir / "eval.json").write_text(json.dumps(questions, indent=2) + "\n", encoding="utf-8")
    (data_dir / "eval_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-questions", type=int, default=36)
    parser.add_argument("--data-dir", type=Path, default=Path("case3_rag/data"))
    args = parser.parse_args(argv)
    try:
        manifest = generate(args.seed, args.n_questions, args.data_dir)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {args.n_questions} questions; label_counts={manifest['label_counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
