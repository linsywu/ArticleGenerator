## ADDED Requirements

### Requirement: Unified task endpoint covers all task types
The `GET /api/tasks/unified` endpoint SHALL return tasks of type `humanize`, `distill`, `direction`, `outline`, `title`, `quality_review`, and `compliance_review` in addition to `generate` and `refine`.

#### Scenario: Humanize tasks appear in unified query
- **WHEN** a `trigger_humanize` Celery task is running or recently completed
- **AND** `GET /api/tasks/unified?status=running,pending` is called
- **THEN** the response includes a task entry with `task_type = "humanize"`
- **AND** the entry includes `target` describing the article being humanized

#### Scenario: Review tasks appear in unified query
- **WHEN** `trigger_quality_review` or `trigger_compliance_review` Celery tasks are running
- **AND** `GET /api/tasks/unified?status=running,pending` is called
- **THEN** the response includes entries with `task_type = "quality_review"` and `"compliance_review"`

#### Scenario: Graceful Celery backend failure
- **WHEN** the Celery result backend is unreachable
- **THEN** the endpoint still returns DB-tracked tasks (generate/refine)
- **AND** logs a warning about Celery backend unavailability

### Requirement: Frontend UnifiedTaskItem interface is complete
The TypeScript `UnifiedTaskItem` interface SHALL declare all fields that the backend returns: `task_type`, `target`, `account_name`, `extra_info`.

#### Scenario: UnifiedTaskItem type covers all API fields
- **WHEN** `TaskCenterView.vue` accesses `t.task_type`, `t.target`, `t.account_name`, `t.extra_info`
- **THEN** TypeScript type checking recognizes these as valid properties
- **AND** produces no implicit `any` errors

### Requirement: TaskCenterView handles all task types
The TaskCenterView SHALL display appropriate icons and labels for all 9 task types (generate, refine, humanize, distill, direction, outline, title, quality_review, compliance_review).

#### Scenario: All task types have icons and labels
- **WHEN** a task of any supported type appears in the task center
- **THEN** the card displays a distinct icon (emoji) for that type
- **AND** the card displays a Chinese label for that type
