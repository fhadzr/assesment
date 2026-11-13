# Proposal

## Why

Case 3 (Enterprise RAG Chatbot) is the assessment's third mandatory prototype and its rubric rows (C3-01…C3-12 in the traceability matrix) are unimplemented — `case3_rag/` holds only the foundation skeleton. It is the assessment's key test of the privacy-by-design rule in its strongest form: access control must be applied **before** LLM context construction, not merely enforced by a system prompt. Cases 1 and 2 established the vertical-slice pattern (schema registry → pipeline → evaluation → dual-surface service → evidence); this change applies it to retrieval-augmented answering over an access-controlled, prompt-injection-bearing knowledge base.

## What Changes

- Add a **synthetic knowledge base generator**: 8–12 documents across HR/IT/Finance/Legal, each with `doc_id`, `section`, metadata, and `allowed_roles` (roles `all`, `hr`, `finance`, `exec`), at least one document containing a malicious prompt-injection payload, all deterministic and regenerable.
- Add a **synthetic evaluation dataset**: 30–40 questions with expected answers and expected citations, each labeled `answerable`, `unanswerable`, or `restricted`, including cross-role access attempts; deterministic and regenerable alongside the KB.
- Add **access-controlled retrieval**: role filtering applied structurally **before** retrieved content is assembled into the prompt; a restricted document can never reach provider context regardless of system-prompt wording; retrieval preserves `doc_id` + `section` for citations.
- Add **prompt-injection defense**: document text is treated as untrusted data, injected instructions never alter the retrieval role or system instructions, and the answerer is grounded so injected "ignore previous instructions" content has no mechanism to take effect; adversarial tests prove it.
- Add **grounded answering with citation + refusal**: answers cite `[doc_id § section]` from retrieved evidence only, refuse (not hallucinate) when the KB lacks support, and refuse when the information exists only in documents the caller's role may not access.
- Add **executable evaluation**: Recall@K, answer correctness, faithfulness/groundedness, citation accuracy, refusal quality, latency, and token/cost from actual provider metadata only — mock and real-provider results kept separate and honestly labeled.
- Add a **service** (FastAPI + CLI sharing one core) with explicit validated role, error handling, and PII-safe logging.
- Add **security tests** (the six required cases) with exported evidence, plus docs (architecture/data-flow, limitations, README), sample Q&A, and traceability matrix updates.

Out of scope: a real vector database or embedding model (8–12 short docs need only deterministic lexical retrieval — see design), streaming, a real auth system (role is a declared, validated attribute — same demo posture as Case 1/2), touching Case 1 or Case 2.

## Capabilities

### New Capabilities
- `rag-knowledge-base`: Seeded synthetic knowledge base (8–12 role-gated docs incl. a prompt-injection doc) and a deterministic evaluation dataset (30–40 labeled questions with expected citations) — feeds retrieval, answering, and evaluation.
- `rag-answering`: Access-controlled retrieval (role filter before prompt), prompt-injection defense, and grounded answering with citation + refusal semantics.
- `rag-service`: CLI + FastAPI sharing one core, explicit role validation, executable evaluation (recall/correctness/faithfulness/citation/refusal/latency/cost), security posture, and evidence.

### Modified Capabilities
- (none — foundation, fraud, and docintel specs are untouched.)

## Impact

- **Code**: `case3_rag/src/rag/` grows modules (knowledge-base generation, evaluation dataset, retrieval, answering, providers, service, CLI, evaluation); tests under `case3_rag/tests/`.
- **Data/artifacts**: KB + eval dataset under `case3_rag/data/` (gitignored except manifests), outputs under `case3_rag/outputs/` (gitignored; evidence copies under `evidence/`).
- **Docs/evidence**: `case3_rag/docs/` populated; matrix C3 rows updated as verified; experiment log + security + sample Q&A evidence.
- **Rubric mapping**: C3-01→`rag-knowledge-base`; C3-02/03/04/05→`rag-answering`; C3-06…C3-12→`rag-service` + docs/evidence.
- **Dependencies**: minimal — the shared stack only (fastapi, uvicorn, pydantic, httpx, pytest); no vector DB, no embedding library (lexical retrieval is deterministic and sufficient at this scale).
