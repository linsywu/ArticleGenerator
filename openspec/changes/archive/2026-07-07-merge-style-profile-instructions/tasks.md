## 1. 蒸馏提示词优化

- [ ] 1.1 更新 `scripts/seed_providers.py` distill 场景的 `system_prompt_template`，改为通用单维度 + 写作指导输出格式
- [ ] 1.2 更新 `tasks.py` 中 `trigger_distill` 的 `dim_labels` 字典，标签改为写作指导风格（如"思维模式"→仍保留，但确认措辞）
- [ ] 1.3 更新 `tasks.py` 中 `trigger_distill` 的 `summary_text` 拼接逻辑，使用 `##` markdown 标题，紧凑排列
- [ ] 1.4 更新数据库中现有 distill 场景配置的 `system_prompt_template`（通过 SQL 或重新执行种子脚本）

## 2. 合并风格变量

- [ ] 2.1 从 `tasks.py` `trigger_generate` 中移除 `style_instructions` 构建代码（约 L129-138）和 variables 中的 `style_instructions` 条目（L156）
- [ ] 2.2 更新 `scripts/seed_providers.py` generate 场景的 `system_prompt_template`：移除 `{{style_instructions}}` 行，将 `{{style_profile}}` 上下文改为"写作风格要求（必须严格遵守）"
- [ ] 2.3 更新数据库中现有 generate 场景配置的 `system_prompt_template`
- [ ] 2.4 更新 `ArticleGeneratorAdm/src/views/ScenarioConfigsView.vue` 中 generate 场景的变量说明，移除 `style_instructions` 条目

## 3. 验证

- [ ] 3.1 运行后端单元测试，确认蒸馏和生成任务不受影响
- [ ] 3.2 运行前端 build，确认 ScenarioConfigsView 编译通过
- [ ] 3.3 新建一个测试账号进行蒸馏，验证输出格式简洁且为写作指导风格
- [ ] 3.4 用新蒸馏的账号触发生成，验证 prompt 中仅包含单一风格变量
