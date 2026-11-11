# synthetic-data Specification

## Purpose

Establishes the conventions that make every dataset in the repository synthetic, seeded, and reproducible from checked-in code — so no data file is ever hand-authored or unverifiable.

## Requirements

### Requirement: All datasets are generated, never hand-authored
Every data file under a case's data, samples, or expected directories SHALL be produced by a generator script that is checked into the repository under that case. No dataset SHALL be created by manual editing.

#### Scenario: Dataset regeneration is byte-identical
- **WHEN** a case's generator script is run twice with the same seed on the same machine
- **THEN** the produced data files are identical (hash-equal) across runs

#### Scenario: Hand-authored data file is detectable
- **WHEN** a data file exists under a case's data directory with no generator script able to produce it
- **THEN** the repository's data-convention check reports it as a violation

### Requirement: Seeds are recorded and configurable
Every generator SHALL accept a seed parameter with a documented default, and the seed used to produce committed data files SHALL be recorded alongside the generator or in its output metadata.

#### Scenario: Default seed is stable
- **WHEN** a generator runs with no explicit seed argument
- **THEN** it uses the documented default seed and records that value in its output metadata

#### Scenario: Different seed yields different data
- **WHEN** a generator runs twice with different seeds
- **THEN** the outputs differ, proving the seed actually drives generation

### Requirement: Generators document their output schema
Each generator SHALL document or emit the schema of its output (field names, types, and meaning) so downstream case code and evaluations can consume the data without reverse-engineering it.

#### Scenario: Schema available for consumers
- **WHEN** a case implementation needs to consume a generated dataset
- **THEN** the schema is available from the generator's documentation or output metadata

### Requirement: No real PII in synthetic data
Synthetic generators SHALL NOT embed real names, addresses, account numbers, or other real-person identifiers; all person- and account-like fields SHALL be fabricated from the generator's random process.

#### Scenario: Generated data contains no real identifiers
- **WHEN** generated datasets are inspected
- **THEN** person and account fields are clearly synthetic fabrications with no verifiable real-world referents
