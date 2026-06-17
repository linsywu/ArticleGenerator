## ADDED Requirements

### Requirement: Hotspot ID validation
The system SHALL validate all hotspot_ids when triggering generation and return HTTP 400 with details for invalid IDs.

#### Scenario: Some invalid IDs
- **WHEN** generation is triggered with non-existent hotspot IDs
- **THEN** the system returns HTTP 400 with {detail, invalid_ids: [...]}

#### Scenario: All valid IDs
- **WHEN** generation is triggered with all valid hotspot IDs
- **THEN** the request proceeds normally
