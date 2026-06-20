## ADDED Requirements

### Requirement: Credential health check works correctly
The system SHALL allow users to trigger a manual credential health check from the CredentialsView page, and the check SHALL complete without errors and refresh the credential list.

#### Scenario: Manual credential health check
- **WHEN** user clicks "检测" button on a credential card
- **THEN** the system calls `POST /api/credentials/{id}/check` and refreshes the credential list, showing the updated status

### Requirement: Collect task execute provides accurate feedback
The system SHALL display accurate feedback after a collection task is manually executed.

#### Scenario: Execute collection task
- **WHEN** user clicks "执行" button on a collection task
- **THEN** the system dispatches the task via `POST /api/collect-tasks/{id}/execute` and shows a success confirmation message

### Requirement: Tree selector state syncs with form data
The collection task form SHALL correctly populate the tree selector when editing an existing task, and SHALL persist the tree selector selections back to the form payload on save.

#### Scenario: Edit existing task restores tree state
- **WHEN** user opens edit dialog for an existing collect task
- **THEN** the track/account tree selector displays previously selected tracks and accounts

#### Scenario: Save task includes tree selections
- **WHEN** user saves a task after selecting tracks and accounts in the tree selector
- **THEN** the selected track IDs and account IDs are serialized and included in the save payload

### Requirement: Material and collect log APIs use typed response models
The system SHALL define Pydantic response schemas for MpMaterial and CollectLog entities and use them in API endpoint response models.

#### Scenario: Material list returns typed response
- **WHEN** `GET /api/materials` is called
- **THEN** the response conforms to the MpMaterialList Pydantic schema

#### Scenario: Collect log list returns typed response
- **WHEN** `GET /api/collect-logs` is called
- **THEN** the response conforms to the CollectLogList Pydantic schema
