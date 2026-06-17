## ADDED Requirements

### Requirement: Business logic in service layer
The system SHALL place generation orchestration logic and article status machine logic in app/services/ modules, not in API router functions.

#### Scenario: Generate trigger through service
- **WHEN** POST /api/generate/trigger is called
- **THEN** the router validates input, calls generate_service, returns result
- **AND** the router function body is ≤30 lines

#### Scenario: Article status update through service
- **WHEN** PATCH /api/articles/{id}/status is called
- **THEN** the router delegates to article_service for status transitions
