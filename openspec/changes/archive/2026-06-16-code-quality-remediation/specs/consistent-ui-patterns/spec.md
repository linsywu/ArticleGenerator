## ADDED Requirements

### Requirement: Unified list page patterns
The system SHALL use PageHeader component and v-loading directive consistently across all list pages.

#### Scenario: All list pages have loading state
- **WHEN** visiting any list page before data loads
- **THEN** a loading indicator is displayed

#### Scenario: No hardcoded light colors
- **WHEN** searching for #f5f7fa in component styles
- **THEN** zero occurrences are found (CSS variables used instead)

#### Scenario: Consistent error handling
- **WHEN** an API error occurs on a list page
- **THEN** an ElMessage.error notification is displayed to the user
