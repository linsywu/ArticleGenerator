## ADDED Requirements

### Requirement: Distill dialog combines reference articles and style profile in split layout

The system SHALL display reference articles on the left and style profile with distillation controls on the right when user opens the distillation dialog.

#### Scenario: Dialog shows articles and profile side by side
- **WHEN** user clicks "风格蒸馏" on an account card
- **THEN** a dialog opens with left panel showing the reference article list and right panel showing style profile (or empty state)

#### Scenario: User can manage reference articles in left panel
- **WHEN** user is in the distillation dialog and not actively distilling
- **THEN** user can add, edit, or delete reference articles in the left panel

#### Scenario: Left panel is read-only during active distillation
- **WHEN** status is "running"
- **THEN** the left panel articles are greyed out and actions are disabled

### Requirement: Style distillation provides real-time progress feedback

The system SHALL poll the distillation status endpoint every 2 seconds and display real-time progress when distillation is running.

#### Scenario: Progress bar updates as dimensions complete
- **WHEN** distillation is running with 3 of 7 dimensions completed
- **THEN** the progress bar shows approximately 43% completion and text displays "已完成 3/7 维度"

#### Scenario: Current dimension is highlighted
- **WHEN** distillation is working on a specific dimension (e.g., "句式特征")
- **THEN** that dimension shows an active indicator while completed dimensions show checkmarks and pending dimensions show waiting state

#### Scenario: Distillation completes successfully
- **WHEN** the status endpoint returns `status: "completed"`
- **THEN** polling stops, the right panel shows the full style profile with all 7 dimensions, and the card badge updates to "画像就绪"

#### Scenario: Distillation fails with error
- **WHEN** the status endpoint returns `status: "failed"`
- **THEN** polling stops, the right panel shows the error message, a "查看详情" button to expand raw error, and a "重试蒸馏" button

#### Scenario: Polling times out after 5 minutes
- **WHEN** distillation status remains "running" for more than 5 minutes
- **THEN** polling stops and the UI displays "蒸馏超时，请稍后重试" with a retry button

#### Scenario: Polling handles network errors
- **WHEN** the status endpoint request fails due to network error
- **THEN** the system retries up to 3 times before displaying "无法获取蒸馏状态"

#### Scenario: Polling stops when dialog closes
- **WHEN** user closes the distillation dialog while distillation is running
- **THEN** polling is stopped and the card badge continues to show "蒸馏中..." based on the account's persisted status

### Requirement: Distillation backend returns granular status

The system SHALL provide a `GET /accounts/{id}/distill/status` endpoint returning the current distillation state.

#### Scenario: Status endpoint returns idle when no task
- **WHEN** account has never been distilled or last distillation is complete
- **THEN** endpoint returns `{ "status": "idle" }`

#### Scenario: Status endpoint returns running with progress
- **WHEN** a distillation task is in progress
- **THEN** endpoint returns `{ "status": "running", "progress": { "completed": N, "total": 7, "current_dimension": "..." } }`

#### Scenario: Status endpoint returns completed
- **WHEN** distillation has finished successfully
- **THEN** endpoint returns `{ "status": "completed", "style_profile_version": N }`

#### Scenario: Status endpoint returns failed
- **WHEN** distillation has failed
- **THEN** endpoint returns `{ "status": "failed", "error": "..." }`

### Requirement: Distillation task calls LLM per dimension

The system SHALL execute 7 independent LLM calls, one per style dimension, updating progress after each call.

#### Scenario: Each dimension completion updates account record
- **WHEN** a single dimension distillation completes
- **THEN** the corresponding field in `style_profile_structured` is updated and `style_profile_status` remains "running" with updated progress metadata

#### Scenario: All 7 dimensions complete
- **WHEN** the 7th dimension distillation completes
- **THEN** `style_profile_status` is set to "ready", `style_profile_version` is incremented, and `style_profile_updated_at` is set to now

#### Scenario: A dimension call fails
- **WHEN** any LLM call for a dimension fails
- **THEN** `style_profile_status` is set to "failed" with the error message, and the task stops processing remaining dimensions

### Requirement: Account model supports word count configuration

The system SHALL persist `word_count_options` (JSON array) and `word_count` (integer) fields on the Account model.

#### Scenario: Word count options are saved and returned
- **WHEN** user saves word count configuration
- **THEN** `word_count_options` (e.g., `[800, 1500, 3000]`) and `word_count` (e.g., `1500`) are persisted and returned in account API responses
