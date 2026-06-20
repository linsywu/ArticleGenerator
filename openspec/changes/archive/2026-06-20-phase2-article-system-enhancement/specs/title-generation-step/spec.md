## ADDED Requirements

### Requirement: CreateView has a title generation step
The article creation wizard in `CreateView.vue` SHALL include a title generation step between outline confirmation and full-text generation, making it a 6-step flow.

#### Scenario: Title step appears after outline
- **WHEN** user confirms the outline in step 4
- **THEN** the wizard advances to step 5 "生成标题"
- **AND** the system calls `POST /api/generate/titles` with the idea, direction, and outline

#### Scenario: Candidate titles are displayed
- **WHEN** the title generation call completes
- **THEN** 3-5 candidate titles are displayed as selectable cards or radio items
- **AND** each title card shows the title text

#### Scenario: User selects and edits a title
- **WHEN** user clicks on a candidate title
- **THEN** the title text appears in an editable input field
- **AND** user can modify the title text

#### Scenario: User confirms title and proceeds
- **WHEN** user clicks "确认标题，生成全文"
- **THEN** the selected/edited title is passed to the full-text generation call
- **AND** the wizard advances to step 6 "生成全文"

### Requirement: Title generation uses the existing backend endpoint
The frontend SHALL call the existing `POST /api/generate/titles` endpoint, which accepts `idea`, `direction_id`, `outline`, and `account_id`.

#### Scenario: Title API call format
- **WHEN** the title generation is triggered
- **THEN** the request body includes `idea`, `direction_id` (the selected direction), `outline` (the confirmed outline points), and `account_id`

#### Requirement: Step numbering updates correctly
The wizard step indicator SHALL show 6 steps total with correct numbering.

#### Scenario: Step indicator shows 6 steps
- **WHEN** the CreateView wizard loads
- **THEN** the step indicator shows steps 1-6: 选择账号, 输入想法, 选择方向, 确认大纲, 生成标题, 生成全文
