## ADDED Requirements

### Requirement: Business logic in service layer
The system SHALL place business logic (prompt building, JSON parsing, multi-table transactions, LLM call orchestration) in app/services/ modules, not in API router functions.

#### Scenario: Generate trigger through service
- **WHEN** POST /api/generate/trigger is called
- **THEN** the router function validates input, calls a service function, and returns the result
- **AND** the router function body is ≤30 lines

#### Scenario: Article status update through service
- **WHEN** PATCH /api/articles/{id}/status is called
- **THEN** the router delegates status machine logic to article_service

#### Scenario: Existing tests pass
- **WHEN** running pytest tests/ -v
- **THEN** all previously passing tests continue to pass
