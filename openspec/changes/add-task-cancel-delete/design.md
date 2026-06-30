## Context

当前状态对比：

| 功能 | `/tasks` | `/task-center` |
|------|----------|----------------|
| 取消 | ✅ 有按钮，调 `cancelTask(task_id)` | ❌ 无 |
| 删除 | ❌ 无 | ❌ 无 |

后端已有 `POST /generate/tasks/{task_id}/cancel`，缺少 `DELETE` 端点。

## Goals / Non-Goals

**Goals:**
- `/task-center` 运行/等待中的任务卡片可取消
- 两个页面的已完成/失败/已取消任务可删除
- 删除只移除任务记录，保留已生成的文章

**Non-Goals:**
- 不删除关联文章（文章有独立的评审/发布流程）
- 不批量操作（单条操作足够）

## Decisions

**1. 删除端点**
`DELETE /api/generate/tasks/{task_id}` — 删除 GenerationTask 记录。只允许删除 `success/failed/cancelled` 状态的任务，`pending/running` 需先取消。

**2. 任务中心取消按钮**
复用 `POST /generate/tasks/{task_id}/cancel`。按钮只在 `pending/running` 状态显示。

**3. 任务中心区分任务来源**
`/tasks/unified` 返回 `task_type`（`generate` / `refine`），前端根据类型调用不同取消/删除端点。RefineTask 暂不支持取消/删除，仅展示。

**4. 删除时清理关联日志**
删除 GenerationTask 时同步删除关联的 generation_logs（`WHERE task_id = ?`），避免孤儿数据。

## Risks / Trade-offs

- 删除不可逆 → 加二次确认弹窗（`ElMessageBox.confirm`）
- RefineTask 暂不支持取消/删除 → 按钮仅对 `task_type === 'generate'` 显示
