## Context

素材中心 → 创作方向 改造为三步弹窗：(1) AI 生成摘要 → (2) 人工确认 → (3) 选账号 → 跳转。需要新增 material-summary 场景配置和对应 Celery 任务。

## Goals / Non-Goals

**Goals:**
- 素材中心生成 AI 摘要，落库 mp_materials.summary
- 用户可在弹窗中查看摘要、选账号后跳转到 /create
- 不改变创建页面已有流程

**Non-Goals:**
- 不改 CreateView 创作流程
- 不新增数据库表

## Decisions

### 决策 1：摘要生成模式

**选**：调 LLM（material-summary 场景），传标题 + markdown 内容。system prompt 模板用 `{{title}}` 和 `{{content}}` 变量。温度 0.5（摘要应稳定）。

**不选**：前端调 `/chat` → 绕过 Celery，但无法落库。选 Celery 任务 + 轮询模式（与 direction/outline 一致）。

### 决策 2：API 端点

`POST /api/materials/{id}/generate-summary` → 返回 task_id → 前端轮询 `GET /api/generate/task/{task_id}/result`。

### 决策 3：Material-summary scenario config

```
scenario: material-summary
system_prompt_template: 将文章内容总结为简洁摘要，保留核心观点
variables: title, content
model: claude-sonnet-4-20250514
temperature: 0.5
max_tokens: 1024
```

### 决策 4：弹窗三态

弹窗新增三个状态：
- **内容加载中**：fetch 素材详情
- **摘要生成中**：轮询 Celery 任务
- **就绪**：已生成摘要（可编辑）+ 账号选择列表

## Risks

- 摘要质量取决于 LLM 输入（markdown 质量），若解析失败则用纯文本 fallback
