## ADDED Requirements

### Requirement: Generate task submission shows confirmation instead of article content
The system SHALL replace the article content display area in the creation flow's final step with a task submission confirmation that guides users to the task center.

#### Scenario: User clicks "确认标题 · 生成全文"
- **WHEN** user has selected a title and clicks the confirm generation button
- **THEN** the system submits the generation task via `POST /generate/trigger`
- **AND** displays a confirmation message "文章生产中，请前往任务中心查看"
- **AND** does NOT poll for task completion or display article content

### Requirement: Confirmation page provides task center navigation
The confirmation page SHALL provide a clearly visible button or link that navigates the user to the task center (`/task-center`).

#### Scenario: User clicks task center link from confirmation page
- **WHEN** user clicks the "前往任务中心" button on the confirmation page
- **THEN** the system navigates to `/task-center` route
- **AND** the task center displays the newly submitted generation task

### Requirement: Generation task submission preserves all existing parameters
The task submission SHALL preserve all existing parameters: selected account, custom topic (title + idea), outline points, word count, and direction.

#### Scenario: Task submitted with complete parameters
- **WHEN** a generation task is submitted with outline, selected title, and direction
- **THEN** the request payload includes `account_id`, `custom_topic` (containing title and idea), `outline`, `word_count`, and `direction`
