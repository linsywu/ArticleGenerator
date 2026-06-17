## ADDED Requirements

### Requirement: Modular Celery tasks
The system SHALL organize Celery tasks into app/tasks/ package with celery_app.py as the Celery instance.

#### Scenario: Worker starts with modular tasks
- **WHEN** celery -A app.celery_app worker is started
- **THEN** all tasks are registered and functional

#### Scenario: No monolithic tasks.py
- **WHEN** checking for app/tasks.py
- **THEN** it does not exist (replaced by app/tasks/ package)
