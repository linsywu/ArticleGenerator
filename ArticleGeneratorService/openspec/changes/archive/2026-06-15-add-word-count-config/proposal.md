## Why

当前文章生成字数硬编码为"1500左右"，无法针对不同账号、不同场景灵活调整。同一账号在公众号和知乎可能需要不同字数（公众号 1500 字、知乎 3000+ 字），但系统不支持。

## What Changes

- 账号表新增字数配置字段：`word_count_options`（可选项列表，value=label 格式）和 `default_word_count`（默认值）
- 账号管理页面新增字数配置表单区域（选项管理 + 默认值选择）
- 文章创作流程"输入想法"步骤新增字数选择器，默认填入账号默认字数
- 后端生成/微调任务将所选字数注入 LLM 提示词，替换硬编码的"1500左右"

## Capabilities

### New Capabilities

- `account-word-count-config`: 账号级字数选项配置，支持多选项 value=label 格式存储，含默认值设置
- `generate-word-count-select`: 文章创作流程中可调字数，不选时使用账号默认值

### Modified Capabilities

None — 现有能力不变，仅新增可选字段。

## Impact

| 层级 | 影响 |
|------|------|
| DB | `accounts` 表新增 2 列（`word_count_options` TEXT, `default_word_count` VARCHAR） |
| 后端 API | Account CRUD schema 新增字段；generate/directions 请求新增可选 `word_count` |
| 后端 Task | `tasks.py` 生成/微调提示词中 `字数1500左右` 改为变量注入 |
| 前端 | `AccountsView.vue` 表单新增字数配置区；`CreateView.vue` 步骤 2 新增字数选择器 |
| LLM 提示词 | `scenario_configs.system_prompt_template` 需添加 `{{word_count}}` 占位（手动在管理后台更新） |
