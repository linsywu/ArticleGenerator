## ADDED Requirements

### Requirement: Centralized constants
The system SHALL define timeout values, default word counts, and pagination limits in app/constants.py.

#### Scenario: No magic numbers in business code
- **WHEN** checking business logic files for timeout or pagination values
- **THEN** they reference constants from app/constants.py, not inline literals

### Requirement: Centralized enums
The system SHALL define article statuses and task statuses as Python Enums in app/enums.py.

#### Scenario: No magic status strings
- **WHEN** checking business logic files for status string literals
- **THEN** they reference Enum members from app/enums.py
