## ADDED Requirements

### Requirement: Async Celery task dispatch
The system SHALL dispatch Celery tasks asynchronously using delay() and immediately return a task_id, without blocking the HTTP request with task.get(timeout=...).

#### Scenario: Trigger generation
- **WHEN** a user triggers article generation via POST /api/generate/trigger
- **THEN** the API returns immediately with {task_id, status: "pending"}
- **AND** no task.get(timeout=...) call blocks the response

#### Scenario: Direction generation
- **WHEN** a user triggers direction generation
- **THEN** the API returns immediately with a task_id

#### Scenario: Outline generation
- **WHEN** a user triggers outline generation
- **THEN** the API returns immediately with a task_id
