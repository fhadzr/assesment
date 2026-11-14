# Spec Delta

## Purpose

Access-controlled retrieval (role filtering applied before prompt construction), prompt-injection defense treating document content as untrusted, and grounded answering with citation and refusal semantics.

## MODIFIED Requirements

### Requirement: Prompt injection defense
Document text SHALL be treated as untrusted data; instructions embedded in retrieved content SHALL NOT change the caller's role, the system instructions, or the access-control decisions, and the answerer SHALL NOT follow "ignore previous instructions" style directives.

Defense SHALL be layered: (a) a deterministic malicious-query gate rejects user queries containing clearly malicious prompt-injection patterns with the existing generic refusal **before** retrieval and provider execution; (b) retrieved content is sanitized so identified malicious instruction sentences are removed before the content reaches any provider, while legitimate factual sentences from the same document are preserved; (c) the assembled prompt frames retrieved passages as untrusted data, never as instructions; (d) an output safeguard examines **each sentence** of a provider answer, and if any sentence is itself an injection directive — at the start, middle, or end of a multi-sentence answer — the **entire answer** is converted to the generic refusal (never partially returned, never spliced); (e) citation enforcement: a substantive answer SHALL be returned only if at least one citation survives the citation post-filter (resolves to a retrieved permitted hit); an answer with empty or all-invalid citations gets the generic refusal with empty citations and refusal=true. Detection is a high-confidence denylist over known patterns — it is NOT a complete defense against all adversarial inputs (obfuscated, translated, or novel payloads may pass the gate; they remain constrained by ACL-first retrieval, sanitization, and the output safeguard), and mock-provider tests are NOT real-LLM security validation.

#### Scenario: Malicious query refused before execution
- **WHEN** a user query contains a clearly malicious injection pattern (e.g. "ignore all previous instructions" combined with revealing restricted documents)
- **THEN** the response is the generic refusal with no citations, and neither retrieval nor any provider is executed for it

#### Scenario: Injected instruction not followed
- **WHEN** a query retrieves the injection document and the injected text asks to "reveal all restricted documents"
- **THEN** the answerer does not reveal restricted documents and the injection has no effect on role or system behavior

#### Scenario: Injection text never returned as the answer
- **WHEN** a retrieved document mixes a legitimate fact with injected instruction text and the query overlaps the injected text
- **THEN** the legitimate fact remains answerable, and the injected instruction sentence never appears as the substantive answer or in citations

#### Scenario: Directive anywhere in a multi-sentence answer is refused
- **WHEN** a provider answer contains an injection-directive sentence at the start, in the middle, or at the end of an otherwise benign multi-sentence answer
- **THEN** the entire answer is replaced with the generic refusal (empty citations, refusal=true); the benign sentences are not partially returned, and a whole-answer match spanning two benign sentences never triggers refusal

#### Scenario: Substantive answers require at least one valid citation
- **WHEN** a provider returns a substantive answer whose citations are empty or all rejected by the citation post-filter (not in the retrieved permitted set)
- **THEN** the result is the generic refusal with empty citations and refusal=true; an answer with at least one valid citation plus invalid ones keeps only the valid citations and remains substantive

#### Scenario: Sanitization preserves legitimate sentences
- **WHEN** a poisoned document contains valid policy facts plus injection text
- **THEN** the sanitized context passed to the provider excludes the injection sentences and retains the factual sentences

#### Scenario: Role cannot be manipulated via content
- **WHEN** a query or document text contains "I am an exec" or similar role claim
- **THEN** the effective role remains the caller's validated role, unchanged by the content

#### Scenario: Injection cannot widen access
- **WHEN** an injection payload in an HR-permitted document or query names finance-only or executive-only content
- **THEN** none of that content appears in the answer, citations, or prompt for the HR caller

#### Scenario: Negative - benign queries unaffected
- **WHEN** an ordinary permitted-role policy question is asked
- **THEN** it is answered normally with citations; the gate and sanitizer do not refuse or degrade it

#### Scenario: Negative - injection attempt detected in adversarial tests
- **WHEN** adversarial tests assert that the injected directive does not alter output
- **THEN** the tests pass because output is grounded to the caller's allowed evidence, not the injected text

#### Scenario: Negative - obfuscated payloads not claimed as blocked
- **WHEN** an adversarial payload evades the denylist gate
- **THEN** the system does not claim detection; the remaining layers (ACL-first retrieval, sanitization, output safeguard) constrain the outcome and this residual risk is documented
