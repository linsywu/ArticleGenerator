## Why

当前 `generate` 场景的 system prompt 中同时存在 `{{style_profile}}` 和 `{{style_instructions}}` 两个风格变量，两者来源相同（都是账号蒸馏结果），信息高度重叠，造成 prompt 冗余。同时蒸馏产出的风格文本偏长且为分析报告风格，不适合直接作为写作风格指导。

## What Changes

- **合并风格变量**：删除 `style_instructions`，模板中仅保留 `{{style_profile}}` 作为唯一的风格指导变量
- **优化蒸馏提示词**：重写 `distill` 场景的 `system_prompt_template`，使每个维度的输出从"分析报告"转变为简洁的"写作指导指令"
- **精简蒸馏汇总**：修正 `tasks.py` 中 `style_profile` 的拼接逻辑，输出精炼的写作指导文本（非分析长文）
- **BREAKING**：移除 `trigger_generate` 中 `style_instructions` 的构建和传参逻辑
- **BREAKING**：`generate` 模板中移除 `{{style_instructions}}` 占位符

## Capabilities

### New Capabilities
- `distill-prompt-optimization`: 蒸馏场景提示词优化，使各维度输出简洁的写作指导指令
- `style-profile-consolidation`: 合并 style_profile 和 style_instructions 为单一风格变量

### Modified Capabilities
（无已有 spec 需要修改）

## Impact

| 范围 | 文件 | 影响 |
|------|------|------|
| 后端 | `ArticleGeneratorService/app/tasks.py` | 移除 `trigger_generate` 中 `style_instructions` 构建逻辑；修改蒸馏 `summary_text` 拼接格式 |
| 种子数据 | `scripts/seed_providers.py` | 更新 `distill` 场景 system prompt 模板；移除 `generate` 模板中 `{{style_instructions}}` 行 |
| 前端 | `ArticleGeneratorAdm/src/views/ScenarioConfigsView.vue` | 更新 generate 场景变量说明，移除 `style_instructions` 条目 |
| LLM Gateway | `LLMService/app/gateway.py` | 无改动（`style_profile` 自动注入逻辑不变） |
| 数据库 | `scenario_configs` 表 | 需要更新 distill 和 generate 场景的 prompt 模板 |
