## ADDED Requirements

### Requirement: Accounts store
The system SHALL cache the accounts list in a Pinia store to avoid repeated fetching when navigating between pages.

#### Scenario: Cross-page account reuse
- **WHEN** a user navigates from one page to another that needs the accounts list
- **THEN** the accounts are not re-fetched if already loaded

### Requirement: Active tasks store
The system SHALL share active task tracking state via a Pinia store.

#### Scenario: Task list consistency
- **WHEN** task state changes in one view
- **THEN** other views display the updated task state
