## ADDED Requirements

### Requirement: API key masking in responses
The system SHALL mask provider API keys in all API responses, displaying only the first 3 characters and last 4 characters with asterisks in between.

#### Scenario: List providers
- **WHEN** a user requests GET /api/providers
- **THEN** each provider's api_key field is masked (e.g., "sk-***abcd")

#### Scenario: Single provider detail
- **WHEN** a user requests GET /api/providers/{id}
- **THEN** the provider's api_key field is masked

#### Scenario: Update with empty api_key
- **WHEN** a user updates a provider with an empty api_key field
- **THEN** the existing api_key is preserved unchanged

#### Scenario: LLMService retrieves full key
- **WHEN** the LLMService needs a provider's api_key for inference
- **THEN** it can retrieve the full unmasked key via internal service layer
