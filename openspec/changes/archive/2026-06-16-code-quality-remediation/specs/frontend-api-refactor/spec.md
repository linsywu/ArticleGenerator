## ADDED Requirements

### Requirement: Domain-split API modules
The system SHALL organize frontend API calls into domain-specific modules (hotspots, articles, accounts, tasks, providers) with a shared axios client and interceptors.

#### Scenario: Shared client with JWT interceptor
- **WHEN** any API request is made
- **THEN** the Authorization header is automatically attached from stored token

#### Scenario: 401 handling
- **WHEN** any API request receives HTTP 401
- **THEN** ElMessage.error displays a message and the user is redirected to /login

#### Scenario: Backward compatible imports
- **WHEN** existing views import API functions
- **THEN** named imports from @/api or @/api/hotspots resolve correctly
