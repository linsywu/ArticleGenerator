## ADDED Requirements

### Requirement: Models package structure
The system SHALL organize SQLAlchemy models into a package (app/models/) with one module per domain entity, re-exported via __init__.py.

#### Scenario: No single models.py over 200 lines
- **WHEN** checking app/models/
- **THEN** no individual file exceeds 200 lines
- **AND** all models remain importable from app.models

### Requirement: Schemas package structure
The system SHALL organize Pydantic schemas into a package (app/schemas/) with one module per domain, re-exported via __init__.py.

#### Scenario: No single schemas.py over 200 lines
- **WHEN** checking app/schemas/
- **THEN** no individual file exceeds 200 lines
- **AND** all schemas remain importable from app.schemas

#### Scenario: All tests pass
- **WHEN** running pytest tests/ -v
- **THEN** all tests pass with the new import structure
