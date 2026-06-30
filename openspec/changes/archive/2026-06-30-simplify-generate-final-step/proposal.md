## Why

创作流程最后一步（步骤 6）展示的是原始 LLM 生成内容，但后端在生成完成后会异步触发"去AI味"（humanize）流水线覆写 `article.content`，导致创作页展示的内容与评审队列中打开的内容不一致。同时，在创作页展示完整文章正文缺乏实际价值——用户在此步骤既不能编辑也不能评审。改为引导用户前往任务中心统一查看生成进度和结果。

## What Changes

- **BREAKING**: 移除创作流程步骤 6 的文章内容展示区域，不再轮询生成结果并展示全文
- 步骤 5 点击"确认标题 · 生成全文"后，直接提交生成任务，提交成功即展示"文章生产中，请前往任务中心查看"
- 提供跳转到任务中心的快捷按钮/链接
- 后端 `trigger_generate` 任务同步执行 humanize 后再返回 success，确保数据一致性（防御性修复，即使前端不再展示也保证 `article.content` 在任务完成时已是最终内容）

## Capabilities

### New Capabilities
- `generate-redirect-to-task-center`: 创作流程提交生成任务后不再展示文章内容，改为引导用户前往任务中心

### Modified Capabilities
<!-- 无已有 spec 需要修改 -->

## Impact

- **前端**: `CreateView.vue` — 移除 `generatedArticle` 展示区域、移除轮询逻辑、移除 `startGenerate()` 中的 `api.getArticle()` 调用、新增任务中心跳转按钮
- **后端**: `tasks.py` — `trigger_generate` 已将 humanize 同步化（上轮修复），无需额外改动
- **用户体验**: 生成流程缩短（不再等待轮询结果），统一通过任务中心管理生成进度
