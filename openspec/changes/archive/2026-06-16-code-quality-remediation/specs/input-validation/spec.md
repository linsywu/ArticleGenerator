## ADDED Requirements

### Requirement: Hotspot ID validation on generate trigger
The system SHALL validate all provided hotspot IDs when triggering generation and return HTTP 400 with details for any invalid IDs.

#### Scenario: All valid IDs
- **WHEN** generation is triggered with all valid hotspot IDs
- **THEN** the request proceeds normally

#### Scenario: Some invalid IDs
- **WHEN** generation is triggered with one or more non-existent hotspot IDs
- **THEN** the system returns HTTP 400 with {detail, invalid_ids: [...]}

#### Scenario: Test coverage
- **WHEN** running pytest tests/ -v
- **THEN** a test case verifies partial invalid ID handling
