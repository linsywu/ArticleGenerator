## ADDED Requirements

### Requirement: Generate prompt unified in system_prompt_template
generate 场景的全部提示词 SHALL 由 `scenario_configs.system_prompt_template` 一个字段承载，不再拆分为 System Prompt + user_prompt 两部分。

#### Scenario: Celery task passes variables instead of user_prompt
- **WHEN** Celery 任务 `trigger_generate` 调用 LLM 服务
- **THEN** 请求体 SHALL 包含 `variables` dict（含 `topic`、`style_instructions`、`outline_section`、`word_count_instruction`），不包含 `user_prompt` 字段

#### Scenario: Template renders all sections
- **WHEN** Gateway 渲染 generate 场景的 system_prompt_template
- **THEN** `{{topic}}`、`{{style_profile}}`、`{{style_instructions}}`、`{{outline_section}}`、`{{word_count_instruction}}` SHALL 被对应变量值替换

#### Scenario: User message is minimal trigger
- **WHEN** 所有变量已通过 system_prompt 传递
- **THEN** User Message SHALL 仅为 `"请开始创作。"` 或等价极简触发语

### Requirement: Template human-editable via admin panel
generate 场景的 `system_prompt_template` SHALL 支持通过管理后台编辑，人类可调整 section 顺序、措辞和权重。

#### Scenario: Admin edits generate template
- **WHEN** 管理员在后台修改 generate 场景的 system_prompt_template
- **THEN** 下次 generate 调用 SHALL 使用新模板渲染

### Requirement: No duplicate variable injection
同一信息 SHALL 不在 System Prompt 中出现两次。`topic` 只在模板的"文章主题"section 出现一次，`style` 相关变量合并在"风格要求"section。

#### Scenario: Single source for topic
- **WHEN** generate 场景渲染完成
- **THEN** 最终 System Prompt 中 `topic` 的值 SHALL 只出现一次
