## ADDED Requirements

### Requirement: Material summary generation endpoint
系统 SHALL 提供 `POST /api/materials/{id}/generate-summary` 端点触发 AI 摘要生成。

#### Scenario: Valid request returns task_id
- **WHEN** 传 `{ title, content }` 给已有素材
- **THEN** 返回 `{ task_id, status: "pending" }`

#### Scenario: Invalid material id
- **WHEN** 素材不存在
- **THEN** 返回 404

### Requirement: Celery task generates and saves summary
Celery 任务 SHALL 调 LLMService `/chat`（scenario=`material-summary`），解析返回内容并保存到 `MpMaterial.summary`。

#### Scenario: Summary saved to database
- **WHEN** LLM 返回摘要文本
- **THEN** `mp_materials.summary` 更新为摘要内容

#### Scenario: LLM returns empty content
- **WHEN** LLM 返回空
- **THEN** 任务标记 failed

### Requirement: material-summary scenario config seed
种子数据 SHALL 包含 `material-summary` 场景配置。

#### Scenario: Seed contains material-summary
- **WHEN** 执行 seed 脚本
- **THEN** `scenario_configs` 表中存在 `scenario = "material-summary"` 记录
