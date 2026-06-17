## ADDED Requirements

### Requirement: Migration execution at startup
The system SHALL execute SQL migration scripts from ArticleGeneratorDatabase/migrations/ in numeric order at application startup.

#### Scenario: Empty database startup
- **WHEN** the application starts against an empty database
- **THEN** all migration scripts are executed in order
- **AND** the resulting table structure matches the migration definitions

#### Scenario: Already-migrated database
- **WHEN** the application starts against an already-migrated database
- **THEN** no duplicate migrations are executed

#### Scenario: Dev mode fallback
- **WHEN** running in development mode
- **THEN** SQLAlchemy create_all is available as a convenience but not the primary path
