# Tasks

## 1. Detection primitives (rag/answering.py)

- [x] 1.1 Add injection-pattern module constants: `INJECTION_OVERRIDE_QUERIES` (instruction-override regexes), `INJECTION_EXFIL_QUERIES` (reveal-restricted intent regexes), `INJECTION_SENTENCE_PATTERNS` (malicious-sentence regexes incl. role-elevation), with `_normalize()` helper; add `is_malicious_query(query)` (override AND exfiltration conjunction) and `sanitize_content(content)` (drop matching sentences, preserve legitimate ones, collapse whitespace)
- [x] 1.2 Strengthen `build_prompt()`: sanitize each retrieved hit's content (content-based, never trusting `metadata.contains_prompt_injection`), drop fully-sanitized-empty hits, wrap context in `<untrusted_documents>` delimiters with fixed untrusted-data preamble; `MockProvider.answer()` skips injection-pattern sentences during grounded selection
- [x] 1.3 Verify `tests/test_answering.py` still passes unchanged (legitimate answering/citation/refusal behavior intact)

## 2. Core gating and output safeguard (rag/core.py)

- [x] 2.1 In `ask()`: return the existing `GENERIC_REFUSAL` (refusal=True, citations=[], hits=[]) for `is_malicious_query(question)` BEFORE `build_prompt`/retrieval/provider execution; apply post-provider output safeguard: answer that is itself an injection-directive sentence → generic refusal with citations stripped
- [x] 2.2 Verify `tests/test_core.py` + `tests/test_providers.py` still pass unchanged (result shape, usage metadata, provider selection, no-fallback semantics untouched)

## 3. Regression tests

- [x] 3.1 Extend `tests/test_injection.py`: exact runtime-reported malicious query → generic refusal, no citations; poisoned HR leave doc (fact + injection) → annual-leave answer remains available, injection text never returned as answer; injection cannot pull fin-only/exec-only content into an HR response; ordinary HR annual-leave query succeeds; ordinary allowed-role retrieval works (hr/finance/exec); unanswerable + restricted → same generic refusal
- [x] 3.2 Extend `tests/test_security.py`: malicious-query-refused-before-execution (provider never invoked), sanitized-context-excludes-injection-sentences (prompt artifact asserted), injection-text-never-the-answer across providers, benign-queries-unaffected
- [x] 3.3 Run the full case3 suite; confirm zero regressions and all new tests pass (108 passed at this stage — historical; the suite grew again in section 5, final counts in 5.7)

## 4. Docs and evidence

- [x] 4.1 Update `case3_rag/docs/architecture.md` (module inventory: sanitizer/gate/safeguard in the data flow) and `case3_rag/docs/limitations.md` (denylist detection is not a complete defense; obfuscated payloads; mock-vs-real distinction stays explicit)
- [x] 4.2 Regenerate `evidence/security_test_results/case3_security.json` via `python scripts/export_security_results.py case3_rag`; confirm all assertions pass (14/14 at this stage — historical; final evidence after section 5 is 18/18, see 5.6)
- [x] 4.3 Validate: `openspec validate rag-injection-hardening` (valid), root `mingw32-make test` (all pass), root `mingw32-make check` (OK), `git diff --check` (clean); evaluation re-run confirmed all metrics identical to the evidence copy (only wall-clock latency differs)

## 5. Final security review refinements (sentence-scoped safeguard, citation enforcement, provider framing)

- [x] 5.1 Sentence-scope the output safeguard: shared `split_sentences()` in `rag/answering.py`; `contains_injection_directive(text)` checks each sentence via `is_injection_sentence()`; `ask()` refuses the WHOLE answer if any sentence is a directive (start/middle/end) — never partially returned; also removes the whole-text false positive where two benign sentences combined across a boundary
- [x] 5.2 Citation enforcement in `ask()`: substantive answer requires ≥1 citation surviving the post-filter; empty or all-invalid citations → `GENERIC_REFUSAL`, empty citations, refusal=true
- [x] 5.3 Fix latent real-provider citation crash: Ollama/Groq now emit canonical `"[doc_id § section]"` strings (previously tuples → `TypeError` in the post-filter on any successful cited real-provider answer)
- [x] 5.4 Groq provider framing: `groq_messages()` sends fixed instruction text as `system` and untrusted passages + question as `user`; unframed prompts degrade to a single user message; Ollama/mock unchanged; NOT claimed to guarantee injection resistance
- [x] 5.5 Regression tests: directive at start/middle/end of multi-sentence answers, whole-answer replacement, benign multi-sentence answers still pass, cross-sentence non-match unit pin (test_injection.py); empty/invalid/valid/mixed citations (test_security.py); groq message split + degradation pin, canonical citation strings for groq+ollama (test_providers.py) — case3 suite alone: 110 passed (was 97); full target incl. root checker tests: 121 passed (see 5.7)
- [x] 5.6 Docs/spec synced: architecture.md (layers ③/④ + provider framing), limitations.md (#7, 7c, 7d), delta spec (clause d/e + 2 new scenarios), design.md (D3/D4/D4b/D4c + risk row); evidence `case3_security.json` regenerated (18/18)
- [x] 5.7 Final validation (authoritative results): `mingw32-make test` — Case 1: 107 passed; Case 2: 78 passed, 1 skipped; Case 3 (+ root checker tests): 121 passed; `python scripts/export_security_results.py case3_rag` — 18/18 security assertions pass; `mingw32-make check` OK; `openspec validate rag-injection-hardening` valid; evaluation re-run identical to evidence metrics (wall-clock latency only)
