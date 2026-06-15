## ADDED Requirements

### Requirement: Word count options stored on account
The system SHALL store word count options on each account as a JSON array of value-label pairs, along with a default selection. Both fields SHALL be nullable for backward compatibility.

#### Scenario: Account has word count options configured
- **WHEN** an account has `word_count_options` set to `[{"value":"1500","label":"1500字左右"},{"value":"3000","label":"3000字"}]`
- **THEN** the account response includes these options for the frontend to render

#### Scenario: Account has no word count options
- **WHEN** an account has `word_count_options` as NULL or empty
- **THEN** the frontend SHALL NOT display a word count selector in the creation flow

#### Scenario: Default word count pre-fills selector
- **WHEN** an account has `default_word_count` set to `"1500"` and the creation flow loads
- **THEN** the word count selector SHALL be pre-selected to `"1500"`

#### Scenario: Creating or updating account with word count options
- **WHEN** the user creates or edits an account with `word_count_options` and `default_word_count`
- **THEN** the values SHALL be persisted to the database and returned in subsequent GET responses
