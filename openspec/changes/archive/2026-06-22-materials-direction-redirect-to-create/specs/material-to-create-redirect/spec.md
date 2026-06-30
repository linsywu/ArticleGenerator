## ADDED Requirements

### Requirement: AI generates summary from material content
素材"创作方向"弹窗打开后 SHALL 自动调 AI 生成摘要，保存到 `mp_materials.summary`。

#### Scenario: Summary generated successfully
- **WHEN** 素材有标题和内容（markdown 或 HTML）
- **THEN** AI 生成摘要并落库，弹窗显示摘要文本

#### Scenario: Summary generation in progress
- **WHEN** Celery 任务正在执行
- **THEN** 弹窗显示"正在生成摘要..."加载状态

#### Scenario: Summary generation fails
- **WHEN** AI 调用失败
- **THEN** 弹窗显示错误信息 + 重试按钮，同时允许跳过直接进入账号选择

### Requirement: User reviews summary then selects account
摘要生成后 SHALL 展示可编辑的摘要文本 + 账号选择列表。

#### Scenario: Summary editable
- **WHEN** 摘要已生成
- **THEN** 用户可在 textarea 中编辑摘要内容

#### Scenario: Select account and confirm
- **WHEN** 用户选择账号并点击确认
- **THEN** 跳转到 `/create?idea=<编辑后的摘要>&account_id=<账号ID>`

### Requirement: CreateView auto-advances when account pre-filled from query
当 `route.query.account_id` 有效时，CreateView SHALL 自动跳到步骤 1。

#### Scenario: Auto-skip account step
- **WHEN** CreateView 加载且 `?account_id=5` 对应账号存在
- **THEN** `currentStep = 1`，展示"输入创作想法"界面
