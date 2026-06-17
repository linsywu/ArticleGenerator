## ADDED Requirements

### Requirement: Backend test coverage for new modules
The system SHALL include pytest tests for providers, scenario_configs, and auth API modules.

#### Scenario: Provider tests
- **WHEN** running pytest tests/test_providers.py -v
- **THEN** tests cover CRUD operations and API key masking

#### Scenario: Auth tests
- **WHEN** running pytest tests/test_auth.py -v
- **THEN** tests cover login success, login failure, and token validation

#### Scenario: Conftest cleanup
- **WHEN** test fixtures clean up database tables
- **THEN** all ORM models are included in the cleanup list

### Requirement: LLMService test rewrite
The system SHALL rewrite LLMService tests to use mock gateway calls and remove mock_mode assertions.

#### Scenario: LLMService tests pass
- **WHEN** running cd LLMService && pytest tests/ -v
- **THEN** all tests pass without mock_mode-specific assertions

### Requirement: Frontend test and typecheck
The system SHALL provide vitest tests for utils/hooks and a typecheck script using vue-tsc.

#### Scenario: Frontend tests pass
- **WHEN** running npm run test
- **THEN** router tests and utility tests pass

#### Scenario: Typecheck passes
- **WHEN** running npm run typecheck
- **THEN** vue-tsc --noEmit reports no errors
