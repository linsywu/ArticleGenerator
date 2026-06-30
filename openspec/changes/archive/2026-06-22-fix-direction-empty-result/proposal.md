## Why

素材中心"创作方向"偶发性返回空 `directions: []`。根因是 direction 场景的 LLM 调用缺少用户消息（只发 system prompt），且 prompt 模板未要求 JSON 格式，加上备用解析器只认英文编号格式，导致 LLM 非确定性输出（temperature=0.9）时有概率解析失败返回空数组。

## What Changes

- Celery 任务 `trigger_direction_generation` 传 `user_prompt` 变量，包含想法、字数、格式指令、可选风格提示
- 更新 `direction` 场景的 system_prompt_template：去掉对 `{{style_profile}}` 的硬依赖，改为仅在用户消息中传递
- 增强备用解析器正则，支持中文编号格式（`方向一：`、`角度1：` 等）
- **BREAKING**: 无

## Capabilities

### New Capabilities
- `direction-robust-parsing`: 创作方向 LLM 响应解析增强——强制 JSON 输出格式 + 中文编号备用解析

### Modified Capabilities
<!-- No existing spec requirements are changing -->

## Impact

- `ArticleGeneratorService/app/tasks.py`: `trigger_direction_generation` 任务（加 `user_prompt`、备用解析正则增强）
- 数据库 `scenario_configs` 表 `direction` 场景记录：更新 `system_prompt_template`（手动在 `/scenario-configs` 页面操作）
- 不影响前端、不影响 API 接口签名
