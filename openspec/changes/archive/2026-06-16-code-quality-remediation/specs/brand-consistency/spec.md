## ADDED Requirements

### Requirement: Consistent branding
The system SHALL use "墨斋" as the unified brand name across index.html title, sidebar, and README.

#### Scenario: Title consistency
- **WHEN** viewing the browser tab title
- **AND** the sidebar header
- **AND** the README project name
- **THEN** all three display "墨斋"

### Requirement: Frontend README
The system SHALL include an ArticleGeneratorAdm/README.md with architecture overview and directory structure documentation.

#### Scenario: README exists
- **WHEN** checking ArticleGeneratorAdm/README.md
- **THEN** it contains architecture overview and directory structure sections
