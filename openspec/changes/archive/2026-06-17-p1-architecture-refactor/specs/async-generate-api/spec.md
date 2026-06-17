## ADDED Requirements

### Requirement: Async task dispatch
The system SHALL use delay() for Celery task dispatch and return task_id immediately, without blocking the HTTP request.

#### Scenario: All generate endpoints return immediately
- **WHEN** any generate API endpoint is called
- **THEN** the response does not wait for task completion
- **AND** no task.get(timeout=...) appears in api/generate.py
