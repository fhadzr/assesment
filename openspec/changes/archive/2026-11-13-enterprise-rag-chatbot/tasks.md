# Tasks

## 1. Knowledge base and evaluation dataset

- [x] 1.1 Add pinned case3 deps (fastapi, uvicorn, pydantic, httpx, pytest — shared stack only, all exact-pinned) to `case3_rag/requirements.txt`, reinstall the case venv, and verify `make test-case3` still passes (smoke)
- [x] 1.2 Implement `rag/generate_kb.py` (seeded, 8–12 docs, HR/IT/Finance/Legal, doc_id/section/allowed_roles/metadata, ≥1 injection doc) and verify `tests/test_kb.py` passes (size honored, all 4 domains, deterministic byte-identical, different-seed differs, out-of-range exits, role vocabulary)
- [x] 1.3 Implement `rag/generate_eval.py` (30–40 questions, labels answerable/unanswerable/restricted, expected answers + citations, cross-role questions) and verify `tests/test_eval_dataset.py` passes (36 default, all 3 labels present, deterministic, ≥3 cross-role, invalid label rejected, expected_citations resolve to real doc/section ids)
- [x] 1.4 Run `make check-data` on the generated KB + eval dataset and verify R1/R2/R3 + secret scan pass with manifests tracked

## 2. Retrieval and access control

- [x] 2.1 Implement `rag/retrieval.py` ACL-first deterministic simplified TF-IDF (validate role → filter eligible by `allowed()` → compute N/df over eligible only → score → rank → top-K), preserving doc_id + section, and verify `tests/test_retrieval.py` passes (top hit correct on a known query, restricted doc never in candidate pool nor statistics, unknown role rejected, citations resolve)
- [x] 2.2 Verify access control is not prompt-deferred: add `tests/test_access_control.py` asserting (a) `retrieve(query, role)` returns a set already excluding disallowed docs, (b) N/df and scores are computed over role-eligible sections only (adding a restricted doc does not change any permitted doc's score or rank), (c) the assembled provider prompt contains zero restricted-doc text (actual prompt captured, not only output), (d) invalid role raises fail-closed, and (e) roles hr, finance, exec each exercise the filter

## 3. Answering, injection defense, refusal

- [x] 3.1 Implement `rag/answering.py` grounded answerer + `MockProvider` (deterministic, grounded to retrieved hits, citation `[doc_id § section]`, refusal marker) and verify `tests/test_answering.py` passes (answerable→answer+citations, unanswerable→refusal, restricted→refusal, citations ⊆ retrieved set)
- [x] 3.2 Implement `OllamaProvider`/`GroqProvider` (httpx, env key for groq, real usage) and verify offline unit tests pass (request shape, error handling, missing-metadata null)
- [x] 3.3 Implement prompt-injection defense (content = untrusted data; post-filter citations; refuse unsupported) and verify `tests/test_injection.py` passes (injected "reveal all restricted" has no effect; role not manipulable via question/content; output grounded)
- [x] 3.4 Implement `rag/core.py` `AskCore` (shared core composing retrieve→answer→post-filter→refusal) and verify `tests/test_core.py` passes (shared result shape, refusal flags, usage metadata)

## 4. Service and CLI

- [x] 4.1 Implement `rag/service/app.py` `POST /ask` (Pydantic role enum, question required, PII-safe logging) and verify `tests/test_api.py` passes (200 valid, 4xx missing role/question/invalid role, no 500, no stack trace)
- [x] 4.2 Implement `rag/cli.py` batch over eval.json and verify `tests/test_cli.py` passes (one result per question, CLI/API agree on same question+role, invalid role exits non-zero)

## 5. Security

- [x] 5.1 Write `tests/test_security.py` covering: restricted-doc-never-in-prompt (prompt captured), injection-ignored, out-of-KB-generic-refusal, cross-role-refused, citations-only-retrieved-permitted, format-valid-but-unretrieved-citation-rejected, role-not-manipulable, invalid-role-fail-closed, and restricted+unanswerable-same-generic-refusal; exercise roles hr/finance/exec; verify all pass
- [x] 5.2 Add PII-safe logging assertions (request id + outcome only, no doc text) across API and CLI and verify they pass
- [x] 5.3 Extend `scripts/export_security_results.py` case map to `case3_rag` and verify `evidence/security_test_results/case3_security.json` is generated with each assertion pass/fail

## 6. Evaluation and evidence

- [x] 6.1 Implement `rag/evaluate.py` (Recall@K, correctness, faithfulness, citation accuracy, refusal quality, latency, honest token/cost separation) and verify `tests/test_evaluation.py` passes (metrics from labels, refusal quality on unanswerable/restricted, mock zero labeled, missing-dataset exits non-zero)
- [x] 6.2 Run evaluation on the dataset with the mock provider, copy to `evidence/experiment_log/case3_evaluation_mock.json` byte-identical, record the exact command
- [x] 6.3 Produce sample Q&A evidence: run CLI over a handful of labeled questions (answerable/unanswerable/restricted), write `evidence/experiment_log/case3_sample_qa.json`, verify byte-identical on re-run

## 7. Docs and matrix

- [x] 7.1 Write `case3_rag/docs/architecture.md` (data-flow diagram KB → retrieve(role filter) → answer → service/CLI → evaluate; every node names a real module) and verify node paths exist
- [x] 7.2 Write `case3_rag/docs/limitations.md` (lexical-retrieval weakness, mock-vs-real gap, role-is-declared-not-auth, injection robustness on real LLMs open) and verify each maps to a design decision
- [x] 7.3 Write `case3_rag/docs/README.md` (setup, run, test, evaluate commands) and verify each documented command runs as written
- [x] 7.4 Update matrix C3 rows (and C3-1x rows for access control/injection/refusal) with real locations, flipping to `verified` only where paths exist and tests pass; verify `make check-evidence` passes
- [x] 7.5 Add Makefile targets `case3-corpus`, `case3-evaluate`, `case3-serve` and verify `make case3-corpus && make case3-evaluate` end-to-end, then `make test` and `make check` all pass

## Workflow follow-up

- Archive the change after review requirements are satisfied (`openspec archive enterprise-rag-chatbot`).
- Verify the archived result (main specs gain `rag-knowledge-base`, `rag-answering`, `rag-service`).
