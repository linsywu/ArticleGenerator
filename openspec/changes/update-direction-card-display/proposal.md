## Why

用户修改了方向生成（direction）的提示词，LLM 输出从简单的 `[{id, title}]` 升级为 7 字段结构（`id`, `title`, `angle`, `core_viewpoint`, `reader_gain`, `article_type`, `check`）。其中 `core_viewpoint`（80-150字核心论点）应替代 `title`（20-30字展示标题）作为传入大纲/标题/文章生成的 `direction` 参数。当前前端只能看到 `id` + `title`，下游也传错了字段，文章创作流程走向不正确。

## What Changes

- 后端 `DirectionItem` schema 新增 `angle`、`core_viewpoint`、`reader_gain`、`article_type`、`check` 五个可选字段
- 前端 `DirectionItem` TypeScript 类型同步
- 前端方向卡片重新设计：标题 + 核心论点简介 + reader_gain + check + 底部标签（angle/article_type），完整展示选题质检信息
- **BREAKING**: 下游 4 处 `selectedDirection.value.title` 改为 `selectedDirection.value.core_viewpoint`，保证大纲/标题/文章生成收到正确的核心论点

## Capabilities

### New Capabilities
- `direction-card-enhancement`: 方向卡片完整展示 7 字段选题质检信息，`core_viewpoint` 替代 `title` 传入后续生成步骤

### Modified Capabilities
<!-- None -->

## Impact

- `ArticleGeneratorService/app/schemas.py` — `DirectionItem` 加 5 个 Optional[str] 字段
- `ArticleGeneratorAdm/src/api/types.ts` — `DirectionItem` 接口同步
- `ArticleGeneratorAdm/src/views/CreateView.vue` — 方向卡片模板 + 样式重设计，4 处 `title` → `core_viewpoint` 下游传递
