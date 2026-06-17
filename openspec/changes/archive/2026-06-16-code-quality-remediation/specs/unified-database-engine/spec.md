## ADDED Requirements

### Requirement: Single database engine for API and Celery
The system SHALL use a single SQLAlchemy engine and session factory for both the FastAPI application and Celery worker processes, defined exclusively in `app/database.py`.

#### Scenario: Celery worker uses shared engine
- **WHEN** a Celery worker task performs a database operation
- **THEN** it uses SessionLocal imported from app.database

#### Scenario: No duplicate create_engine
- **WHEN** searching for create_engine in the codebase
- **THEN** it appears only in app/database.py

#### Scenario: SQLite uses absolute path
- **WHEN** DATABASE_URL specifies a SQLite path
- **THEN** the path is resolved to an absolute path before use
