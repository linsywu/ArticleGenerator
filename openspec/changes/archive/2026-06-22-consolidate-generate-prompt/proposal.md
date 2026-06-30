## Why

当前文章生成（generate）的提示词被拆成 System Prompt 和 User Message 两部分，彼此不知道对方说了什么——System 说"根据标题和风格创作"，User 说"严格按照大纲逐段写作"，导致 LLM 生成的文章与用户确认的大纲毫无关系。同时变量命名混乱（`hotspot_title` 在创建流程中实际是用户自拟标题）、大纲步骤阻塞流程但 LLM 不遵循、humanize 重写丢失大纲结构。需要统一提示词架构，让人类可编辑、LLM 可遵循、流程更流畅。

## What Changes

- **BREAKING**：generate 场景的提示词从 System + User 分拆改为 System Prompt 统一承载，User Message 降级为极简触发语
- generate 场景的 `system_prompt_template` 新增 `{{outline_section}}`、`{{style_instructions}}`、`{{word_count_instruction}}` 占位符，由 Gateway 统一渲染
- Celery 任务 `trigger_generate` 不再拼接 `user_prompt` 字符串，改为传递分片变量
- 变量 `hotspot_title` 重命名为 `topic`，System Prompt 模板中 `热点标题` 改为 `文章主题`
- 前端大纲步骤降级为可选（默认跳过），后端 `outline` 变量改为 `outline_section`（整段或空字符串）
- `trigger_humanize` 任务新增 `outline_section` 参数，去 AI 味重写时保持大纲结构
- 种子数据中 generate 场景的模板更新为新格式

## Capabilities

### New Capabilities

- `generate-prompt-consolidation`: generate 场景提示词统一由 system_prompt_template 承载，消除 System/User 指令冲突
- `outline-optional-flow`: 大纲步骤从前端默认必选改为可选，后端支持无大纲生成
- `topic-variable-rename`: 变量 `hotspot_title` 重命名为 `topic`，覆盖热点和自定义两种来源
- `humanize-outline-awareness`: humanize 步骤接收大纲上下文，重写时保持结构约束

### Modified Capabilities

<!-- No existing specs to modify -->

## Impact

- **后端**：`tasks.py`（trigger_generate 改为传 variables、trigger_humanize 新增 outline_section）、`gateway.py`（渲染逻辑不变但 variables 变多）、`generate_service.py`（参数透传）
- **前端**：`CreateView.vue`（大纲步骤改为可选、变量名对齐）、`client.ts` 和 `modules/tasks.ts`（API 参数名更新）
- **数据库**：`scenario_configs` 表中 generate 和 humanize 场景的 `system_prompt_template` 更新
- **种子数据**：`seed_providers.py` 中 generate 和 humanize 模板更新
- **LLM Service**：Gateway 渲染逻辑兼容新增的 variables，`/generate` 端点保持兼容
