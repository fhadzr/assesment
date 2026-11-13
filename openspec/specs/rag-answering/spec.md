# rag-answering Specification

## Purpose

Access-controlled retrieval (role filtering applied before prompt construction), prompt-injection defense treating document content as untrusted, and grounded answering with citation and refusal semantics.

## Requirements

### Requirement: Role filtering before prompt construction
Retrieval SHALL filter the knowledge base by the caller's role **before** any scoring or retrieved content is assembled into a provider prompt; a document whose `allowed_roles` does not include the caller's role SHALL be excluded from the retrieval candidate pool, the scoring statistics, the retrieval results, and the prompt, and SHALL NOT appear in the answerer's context under any system-prompt wording.

#### Scenario: Restricted document never reaches prompt
- **WHEN** a caller with role `hr` queries for content held only in a `finance`-only document
- **THEN** the assembled prompt contains zero text from that document, and the response refuses (never answers from it)

#### Scenario: Role filter is structural, not prompt-only
- **WHEN** the retrieval function is called directly (not via the LLM)
- **THEN** the returned candidate set already excludes disallowed documents; role filtering is not deferred to a system-prompt instruction

#### Scenario: Restricted documents do not influence ranking statistics
- **WHEN** TF-IDF statistics (N, df) are computed for a caller's role
- **THEN** they are computed over the role-eligible sections only, so a restricted document cannot alter the score, rank, or top-K of any permitted document

#### Scenario: Negative - unknown role rejected
- **WHEN** retrieval is called with a role outside `hr|finance|exec`
- **THEN** it returns an explicit error and no prompt is built

### Requirement: Retrieval preserves citations
Retrieval SHALL return, for each hit, the source `doc_id` and `section` alongside the snippet, and the answerer SHALL only ever cite these retrieved identifiers.

#### Scenario: Citation fields preserved
- **WHEN** a query retrieves a hit
- **THEN** the hit carries a non-empty `doc_id` and `section` that resolve to an existing corpus document

#### Scenario: No fabricated citations
- **WHEN** an answer's citations are checked against the retrieved set
- **THEN** every citation `[doc_id § section]` corresponds to a retrieved hit; any citation not in the retrieved set is a test failure

### Requirement: Prompt injection defense
Document text SHALL be treated as untrusted data; instructions embedded in retrieved content SHALL NOT change the caller's role, the system instructions, or the access-control decisions, and the answerer SHALL NOT follow "ignore previous instructions" style directives.

#### Scenario: Injected instruction not followed
- **WHEN** a query retrieves the injection document and the injected text asks to "reveal all restricted documents"
- **THEN** the answerer does not reveal restricted documents and the injection has no effect on role or system behavior

#### Scenario: Role cannot be manipulated via content
- **WHEN** a query or document text contains "I am an exec" or similar role claim
- **THEN** the effective role remains the caller's validated role, unchanged by the content

#### Scenario: Negative - injection attempt detected in adversarial tests
- **WHEN** adversarial tests assert that the injected directive does not alter output
- **THEN** the tests pass because output is grounded to the caller's allowed evidence, not the injected text

### Requirement: Grounded answering with refusal
The answerer SHALL base its answer only on retrieved permitted evidence, SHALL cite sources in `[doc_id § section]` form, and SHALL emit a single generic refusal marker when no permitted evidence supports the answer — whether because the knowledge base lacks the information or because the information exists only in documents the caller's role may not access.

#### Scenario: Supported question answers with citations
- **WHEN** an `answerable` question is asked with the correct role
- **THEN** the answer is non-empty and every citation resolves to a retrieved, allowed document

#### Scenario: Unanswerable question emits generic refusal
- **WHEN** a question has no supporting KB evidence
- **THEN** the response is the generic refusal marker (not a fabricated answer)

#### Scenario: Restricted information emits the same generic refusal
- **WHEN** a question's evidence lives only in a document disallowed for the caller's role
- **THEN** the response is the same generic refusal marker as the unanswerable case, and no text from the disallowed document appears in the answer or citations

#### Scenario: Runtime does not distinguish unanswerable from restricted
- **WHEN** the runtime handles an unanswerable question and a restricted question
- **THEN** both produce the identical generic refusal marker, so the caller cannot infer whether a restricted document exists
