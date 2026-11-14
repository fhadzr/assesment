"""Shared answering core (tasks 3.4, 4.1, 4.2).

Composes query gate → retrieval → prompt (sanitized) → provider → citation
post-filter → refusal → output safeguard.

The post-filter enforces citation integrity: a citation is kept only if its
(doc_id, section) is in the retrieved permitted hit set. A format-valid but
unretrieved citation is stripped. A substantive answer is returned only if at
least one valid citation survives; if the answer becomes unsupported (empty,
a refusal, or all citations stripped/absent), the result is the generic
refusal with empty citations.

Injection hardening (rag-injection-hardening change):
  - a clearly malicious query is refused BEFORE retrieval/provider execution
    (denylist gate — see the SECURITY BOUNDARY note in rag.answering; it is a
    high-confidence filter, not a complete adversarial defense);
  - an answer in which ANY sentence is an injection directive (start, middle,
    or end of a multi-sentence answer) is converted to the generic refusal,
    so attacker-controlled directives are never returned as substantive
    answers regardless of provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rag.answering import (
    SYSTEM_PROMPT,
    build_prompt,
    contains_injection_directive,
    extract_citations,
    is_malicious_query,
    make_provider,
)
from rag.retrieval import InvalidRoleError

GENERIC_REFUSAL = "REFUSAL: insufficient permitted evidence"


@dataclass
class AnswerResult:
    answer: str
    citations: list[str]
    refusal: bool
    hits: list[dict]
    usage: dict = field(default_factory=dict)
    error: str | None = None


def _is_refusal(text: str) -> bool:
    return text.strip().upper().startswith("REFUSAL")


def ask(question: str, role: str, docs: list[dict], provider_name: str = "mock", k: int = 3, **provider_kwargs) -> AnswerResult:
    # Query gate FIRST: a clearly malicious prompt-injection query never
    # reaches retrieval, prompt construction, or a provider. Same generic
    # refusal as unanswerable/restricted, so the caller learns nothing about
    # detector coverage. (Denylist gate: high-confidence patterns only.)
    if is_malicious_query(question):
        return AnswerResult(answer=GENERIC_REFUSAL, citations=[], refusal=True, hits=[])

    try:
        prompt, hits = build_prompt(question, role, docs, k=k)
    except InvalidRoleError as exc:
        return AnswerResult(answer="", citations=[], refusal=True, hits=[], error=str(exc))

    provider = make_provider(provider_name, **provider_kwargs)
    raw = provider.answer(prompt, hits, question)

    # citation post-filter: keep only citations in the retrieved permitted set
    hit_pairs = {(h["doc_id"], h["section"]) for h in hits}
    kept = []
    for c in raw.get("citations", []):
        # extract (doc_id, section) from the "[doc_id § section]" string
        parsed = extract_citations(c)
        if not parsed:
            continue
        doc_id, section = parsed.pop()
        if (doc_id, section) in hit_pairs:
            kept.append(c)
    answer = raw.get("answer", "").strip()

    # refusal if unsupported
    if _is_refusal(answer) or (not answer) or (not hits):
        return AnswerResult(answer=GENERIC_REFUSAL, citations=[], refusal=True, hits=hits, usage=raw.get("usage", {}))

    # Output safeguard: if ANY sentence of the answer is itself an injection
    # directive (start, middle, or end of a multi-sentence answer), the whole
    # answer is replaced with the generic refusal rather than partially
    # returned — an attacker-controlled directive must never reach the caller,
    # and splicing the answer open would leak which sentence tripped it. Works
    # for any provider, including one that ignored the untrusted-data framing.
    if contains_injection_directive(answer):
        return AnswerResult(answer=GENERIC_REFUSAL, citations=[], refusal=True, hits=hits, usage=raw.get("usage", {}))

    # Citation enforcement: a substantive answer must carry at least one
    # citation that survived the post-filter (i.e. resolved to a retrieved
    # permitted hit). An answer whose citations were all stripped — or that
    # never cited anything — is unsupported, so it gets the same generic
    # refusal with empty citations (never an uncited substantive answer).
    if not kept:
        return AnswerResult(answer=GENERIC_REFUSAL, citations=[], refusal=True, hits=hits, usage=raw.get("usage", {}))

    return AnswerResult(answer=answer, citations=kept, refusal=False, hits=hits, usage=raw.get("usage", {}))
