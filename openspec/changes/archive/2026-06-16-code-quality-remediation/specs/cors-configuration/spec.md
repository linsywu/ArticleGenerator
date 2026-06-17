## ADDED Requirements

### Requirement: Secure CORS configuration
The system SHALL configure CORS with a specific origin list rather than wildcard, and SHALL NOT combine allow_origins=["*"] with allow_credentials=True.

#### Scenario: Development CORS
- **WHEN** CORS_ORIGINS is set to http://localhost:5173
- **THEN** the frontend dev server can make cross-origin requests with credentials

#### Scenario: Production CORS
- **WHEN** CORS_ORIGINS is set to a specific production domain
- **THEN** only that domain can make cross-origin requests

#### Scenario: No wildcard + credentials combination
- **WHEN** the application starts
- **THEN** allow_origins does not equal ["*"] when allow_credentials is True
