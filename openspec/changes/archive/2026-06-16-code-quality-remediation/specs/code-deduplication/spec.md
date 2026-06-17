## ADDED Requirements

### Requirement: Shared OpenAI-compatible adapter base
The system SHALL provide a shared base class for OpenAI-compatible LLM adapters to reduce duplication.

#### Scenario: Adapter registration
- **WHEN** a new OpenAI-compatible provider is registered
- **THEN** it can extend the shared base class with minimal configuration

### Requirement: Remove unused code
The system SHALL remove generator.py mock code, unused get_db_session, and other dead code identified by grep.

#### Scenario: No dead code references
- **WHEN** searching for removed function names in the codebase
- **THEN** zero references are found
