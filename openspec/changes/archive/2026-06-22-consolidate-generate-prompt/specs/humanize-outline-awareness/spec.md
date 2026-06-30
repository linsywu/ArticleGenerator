## ADDED Requirements

### Requirement: Humanize receives outline context
去 AI 味重写任务 `trigger_humanize` SHALL 接收 `outline_section` 参数（当 generate 阶段使用了大纲时），并将大纲上下文传递给 LLM。

#### Scenario: Humanize with outline
- **WHEN** `trigger_generate` 使用了大纲生成文章，随后触发 `trigger_humanize`
- **THEN** `trigger_humanize` 的 variables SHALL 包含 `outline_section`，其值与 generate 阶段一致

#### Scenario: Humanize without outline
- **WHEN** `trigger_generate` 未使用大纲，随后触发 `trigger_humanize`
- **THEN** `trigger_humanize` 的 variables 中 `outline_section` SHALL 为空字符串，humanize 模板中的 `{{outline_section}}` SHALL 渲染为空

### Requirement: Humanize template includes outline placeholder
humanize 场景的 `system_prompt_template` SHALL 包含 `{{outline_section}}` 占位符，位置在文章内容之前，确保 LLM 在重写前理解结构约束。

#### Scenario: Humanize template renders outline constraint
- **WHEN** humanize 场景渲染模板且 `outline_section` 非空
- **THEN** LLM 收到的 System Prompt SHALL 包含"请保持以下文章结构不变"及大纲内容

### Requirement: Article structure preserved after humanization
当 generate 阶段使用了大纲时，humanize 后的文章 SHALL 保持与大纲一致的段落结构和顺序。

#### Scenario: Structure preserved
- **WHEN** 用户确认了大纲并生成全文，humanize 完成重写
- **THEN** 最终文章的段落数 SHALL 不少于大纲要点数，每个大纲要点在文中 SHALL 有对应段落
