## Context

素材中心的"💡 创作方向"按钮目前是占位状态（`ElMessage.info("创作方向功能将在后续版本中开放")`）。后端 API (`POST /generate/directions`)、Celery 任务 (`trigger_direction_generation`)、前端 API 层 (`generateDirections()` + `DirectionItem` 类型) 均已在文章创作向导 (CreateView) 中完整实现并验证通过。

本次变更只需在 MaterialsView 中补齐前端 UI，复用全部已有基础设施。

**参考实现**: `CreateView.vue` 第 233-261 行的 `generateDirections()` 函数——调用 API → 轮询 task result → 解析 `result.directions`。

## Goals / Non-Goals

**Goals:**
- 素材中心表格每行的"💡 创作方向"按钮点击后弹出方向生成弹窗
- 弹窗内以素材文章标题作为 idea 调用方向生成 API
- 轮询等待生成完成后展示 3-5 个方向卡片
- 用户可选择一个方向，点击后跳转到 `/create` 页面（携带预填参数）

**Non-Goals:**
- 不修改后端 API 或 Celery 任务
- 不在弹窗内完成完整的文章创作流程（跳转到 CreateView 处理）
- 不新增数据库表或字段
- 不改变 MaterialsView 的表格结构或数据加载逻辑

## Decisions

### 1. 弹窗形式：Dialog vs Drawer
**选择: Dialog (el-dialog)**

- 方向生成是一个聚焦的、短流程的操作，Dialog 更合适
- 宽度 600px 足够展示 3-5 个方向卡片
- 与 CreateView 的步骤式向导区分开，避免用户混淆

### 2. 组件拆分：内联 vs 独立组件
**选择: 独立组件 `MaterialsDirectionDialog.vue`**

- MaterialsView.vue 已经 ~500 行，内联会让文件进一步膨胀
- 独立组件便于后续复用（如 CollectTasksView 也可能需要）
- 组件放在 `ArticleGeneratorAdm/src/components/` 下

### 3. 跳转方式：路由参数 vs query 参数
**选择: query 参数 (`?idea=xxx&direction=xxx`)**

- CreateView 可以读取 query 参数预填 Step 2 的 idea 和 Step 3 的 direction
- 用户刷新页面不会丢失上下文
- 简单透明，无需 pinia 跨页面状态

### 4. 轮询逻辑：复用 vs 重写
**选择: 复用 `api.generateDirections()` + 相同的轮询模式**

- CreateView 已有成熟的 2s 间隔 × 30 次轮询模式
- 在弹窗中直接使用，保持一致性

## Risks / Trade-offs

- **[轮询超时]**: 如果 LLM 响应慢（>60s），弹窗会显示超时提示 → 提示用户重试，不阻塞 UI
- **[弹窗关闭时机]**: 用户在生成中关闭弹窗 → 任务仍在后台执行，不会取消 Celery 任务（Celery 不支持取消），但前端停止轮询，无副作用
- **[CreateView query 参数兼容]**: CreateView 当前未处理 query 参数 → 需要小改 CreateView 的 `onMounted` 读取 `route.query`，改动量小

## Open Questions

- 选择方向后是否需要同时携带 `account_id` 跳转？（素材行已有 `account_id`，可以一并传递）
