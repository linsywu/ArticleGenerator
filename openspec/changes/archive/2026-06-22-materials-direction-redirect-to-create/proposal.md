## Why

素材中心"创作方向"当前在弹窗中调 API 生成方向（account_id=0），与创建页面重复。应改为：
1. AI 生成素材摘要（新功能，落库）
2. 人工确认摘要
3. 选账号 → 摘要带入创建流程

## What Changes

- **新增** scenario config `material-summary`：AI 摘要生成模板
- **新增** `POST /api/materials/{id}/generate-summary`：调 LLM 生成摘要并落库
- **新增** Celery 任务 `trigger_material_summary`：构建变量 → 调 LLM → 解析 → 存 MpMaterial.summary
- **改** `MaterialsDirectionDialog.vue`：摘要生成 + 账号选择 + 跳转
- **改** `scripts/seed_providers.py`：加 material-summary 场景种子

## Capabilities

### New Capabilities
- `material-summary-generation`: AI 自动生成素材摘要并落库
- `material-to-create-redirect`: 素材中心创作方向 → 摘要确认 → 选账号 → 跳转创建页

## Impact

- 后端：`app/api/materials.py`（新端点）、`app/tasks.py`（新 Celery 任务）
- 前端：`MaterialsDirectionDialog.vue`（重写）
- 配置：`scripts/seed_providers.py`（新场景种子）
- 数据库：`mp_materials.summary` 已有字段，无需迁移
