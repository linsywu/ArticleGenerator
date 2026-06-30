## 1. 后端 — Celery 任务重构

- [ ] 1.1 `trigger_generate` 参数 `hotspot_title` 改为 `topic`
- [ ] 1.2 移除 `user_prompt` 字符串拼接逻辑，改为构建 variables dict（`topic`、`style_instructions`、`outline_section`、`word_count_instruction`）
- [ ] 1.3 `outline` 参数处理：有 outline 时构建完整 `outline_section`（含标题和约束语），无 outline 时为空字符串
- [ ] 1.4 LLM 服务调用改为走 `/chat` 端点（传 `scenario="generate"` + `variables`），不再走 `/generate` 端点传 `user_prompt`
- [ ] 1.5 `trigger_humanize` 新增 `outline_section` 参数，传入 variables

## 2. 后端 — 服务层 & Schema 适配

- [ ] 2.1 `generate_service.py`：`custom_topic` → `topic` 参数透传调整
- [ ] 2.2 `schemas.py`：`GenerateRequest.outline` 保持兼容，新增 `outline_section` 不暴露给 API（内部构建）
- [ ] 2.3 `api/generate.py`：触发端点适配新参数名

## 3. 后端 — 种子数据 & 数据库模板

- [ ] 3.1 `seed_providers.py`：更新 generate 场景的 `system_prompt_template` 为新格式（统一模板含 `{{topic}}`、`{{outline_section}}` 等占位符）
- [ ] 3.2 `seed_providers.py`：更新 humanize 场景的 `system_prompt_template`，新增 `{{outline_section}}` 占位符
- [ ] 3.3 提供 SQL 更新语句，用于手动更新已有数据库中 generate 和 humanize 场景的模板

## 4. LLM 服务 — Gateway & 端点兼容

- [ ] 4.1 `gateway.py`：确认渲染逻辑兼容新增 variables（无需改动，`_render_prompt` 已通用）
- [ ] 4.2 `main.py`：`/generate` 端点兼容新旧两种调用方式（`hotspot_title` 内部转为 `topic`）
- [ ] 4.3 User Message 降级：Gateway 在 variables 不含 `user_prompt` 时使用默认触发语 `"请开始创作。"`

## 5. 前端 — 流程 & API 适配

- [ ] 5.1 `CreateView.vue`：大纲步骤改为可选，新增"跳过，直接生成全文"按钮（默认行为）和"生成大纲预览"按钮
- [ ] 5.2 `CreateView.vue`：`startGenerate()` 中 `outline` 参数改为可选，未使用大纲时传空数组
- [ ] 5.3 `client.ts`：`triggerGenerateWithOutline` 参数名从 `customTopic` 改为 `topic`（外部调用方可见）
- [ ] 5.4 `modules/tasks.ts`：同步更新参数名

## 6. 验证

- [ ] 6.1 运行后端 pytest 确认 `trigger_generate` 和 `trigger_humanize` 测试通过
- [ ] 6.2 运行 LLM 服务测试确认 Gateway 渲染新模板正确
- [ ] 6.3 运行前端 vitest 确认组件逻辑
- [ ] 6.4 启动 dev server，手动走一遍"无大纲"创建流程，确认文章正常生成
- [ ] 6.5 启动 dev server，手动走一遍"有大纲"创建流程，确认文章遵循大纲
- [ ] 6.6 确认管理后台可编辑 generate 场景的 system_prompt_template
