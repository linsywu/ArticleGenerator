## ADDED Requirements

### Requirement: Wizard guides new account creation step by step

The system SHALL present a three-step wizard when the user clicks "新增账号", replacing the current single-dialog-with-tabs approach.

#### Scenario: User completes wizard with valid inputs
- **WHEN** user fills in platform and account name in Step 1, adds at least one reference article in Step 2, clicks "开始蒸馏" in Step 3
- **THEN** system creates the account, saves reference articles, triggers distillation, closes the wizard, and shows the new account card with "蒸馏中..." status

#### Scenario: User cannot proceed without required fields
- **WHEN** user has not filled in platform or account name in Step 1
- **THEN** the "下一步" button is disabled and validation errors are shown

#### Scenario: User cannot proceed without reference articles
- **WHEN** user has no reference articles in Step 2
- **THEN** the "下一步" button is disabled and a hint "请添加至少一篇文章" is shown

#### Scenario: User navigates back to edit previous step
- **WHEN** user clicks "上一步" on Step 2 or Step 3
- **THEN** the wizard returns to the previous step with all entered data preserved

#### Scenario: User cancels wizard mid-flow
- **WHEN** user closes the wizard dialog or clicks cancel
- **THEN** no account is created and all entered data is discarded

### Requirement: Account card displays operation buttons instead of single click-to-dialog

The system SHALL display action buttons on each account card for independent operations, replacing the old single-click-to-tabbed-dialog pattern.

#### Scenario: Card shows three operation buttons
- **WHEN** account card is rendered
- **THEN** card displays "基本信息", "风格蒸馏", "字数配置" buttons

#### Scenario: Card shows style profile status badge
- **WHEN** account has `style_profile_status` = "ready"
- **THEN** card shows green "画像就绪 v{n}" badge
- **WHEN** account has `style_profile_status` = "running"
- **THEN** card shows blue "蒸馏中..." badge with loading animation
- **WHEN** account has `style_profile_status` = "failed"
- **THEN** card shows red "蒸馏失败" badge
- **WHEN** account has no style profile (idle/none/null)
- **THEN** card shows orange "待蒸馏" badge

### Requirement: Basic info editing uses standalone dialog

The system SHALL open a standalone dialog for editing account platform and name when user clicks "基本信息" on a card.

#### Scenario: Edit basic info and save
- **WHEN** user modifies platform or account name in the dialog and clicks "保存"
- **THEN** account is updated and the card reflects the new values

### Requirement: Word count configuration uses standalone dialog

The system SHALL open a standalone dialog for managing word count options when user clicks "字数配置" on a card.

#### Scenario: Add and remove word count options
- **WHEN** user adds or removes word count values and selects a default, then clicks "保存"
- **THEN** word count configuration is saved to the account
