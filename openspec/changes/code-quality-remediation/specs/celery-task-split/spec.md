## ADDED Requirements

### Requirement: Modular Celery task structure
The system SHALL organize Celery tasks into a package with separate modules for generation, review, and distillation, with the Celery app instance in app/celery_app.py.

#### Scenario: Celery worker starts
- **WHEN** running celery -A app.celery_app worker -l info
- **THEN** the worker starts successfully and registers all tasks

#### Scenario: No monolithic tasks.py
- **WHEN** checking app/tasks.py
- **THEN** it does not exist (replaced by app/tasks/ package)

#### Scenario: Task names preserved
- **WHEN** a task is dispatched by name
- **THEN** it maps to the correct function in the new module structure
