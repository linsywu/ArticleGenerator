## ADDED Requirements

### Requirement: Accounts store
The system SHALL cache accounts in a Pinia store to prevent repeated fetching on page navigation.

#### Scenario: Cross-page reuse
- **WHEN** user navigates between pages needing the accounts list
- **THEN** accounts are not re-fetched if already loaded

### Requirement: Tasks store
The system SHALL share active task tracking via a Pinia store with global singleton polling.
