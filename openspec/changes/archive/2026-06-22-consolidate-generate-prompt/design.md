## Context

当前 generate 场景的提示词架构：

```
System Prompt (DB: scenario_configs)     User Message (Celery: tasks.py)
─────────────────────────────────────    ────────────────────────────────
你是一个专业的内容创作者。              以"xxx"为题，写一篇文章。
根据热点标题和风格要求...
                                        【风格要求 - 必须严格遵守】
风格要求：{{style_profile}}             句式：...
                                        用词：...
热点标题：{{hotspot_title}}             禁忌：...
                                        留白：...
                                        【写作大纲】
                                        1. 要点一
                                        2. 要点二
                                        请严格按照以上大纲逐段写作。
                                        字数1500左右。
```

问题：
- System 定义角色时完全不知道大纲的存在，LLM 按 System 框架理解任务
- `hotspot_title` 在 System 和 User 中各出现一次，User 里的实际值是 `editedTitle\n\nidea`
- 风格在两个地方各注入一次（旧版文本画像 vs 结构化 7 维度）
- `user_prompt` 字符串由 Celery 硬编码拼接，人类无法通过后台编辑权重和顺序

## Goals / Non-Goals

**Goals:**
- 将所有提示词统一到 `scenario_configs.system_prompt_template` 一个字段
- Celery 只负责传 variables，Gateway 负责渲染
- 变量命名对齐业务语义（`hotspot_title` → `topic`）
- 大纲从必选步骤降级为可选，未启用时相关 section 完全消失
- Humanize 步骤感知大纲，重写时保持结构
- 管理员可在后台编辑提示词模板

**Non-Goals:**
- 不改变 Gateway 的渲染引擎（仍然是 `{{var}}` 简单替换）
- 不改变 adapter 层（OpenAI/Anthropic 消息组装不变）
- 不改变其他场景（direction、outline、title、review 等）
- 不引入新的 LLM 调用

## Decisions

### Decision 1: System Prompt 承载全部指令

**选择**：全部提示词写入 `system_prompt_template`，User Message 只保留 `"请开始创作。"` 作为极简触发语。

**原因**：当前项目使用的所有 LLM（DeepSeek、Anthropic）都支持 System + User 角色分离，但 System Prompt 权重更高。把大纲、风格、字数全部放进 System Prompt，确保 LLM 在系统层面就理解全部约束。

**备选**：合并到 User Message。不选——System 角色定义仍有价值，且 System 权重更高。

### Decision 2: 变量分片而非整段

**选择**：模板使用分片变量（`{{topic}}`、`{{style_instructions}}`、`{{outline_section}}`、`{{word_count_instruction}}`），而非一个 `{{user_prompt}}` 大变量。

**原因**：人类可独立调整每个 section 的顺序和措辞。无大纲时 `{{outline_section}}` 渲染为空字符串，整个 section 自然消失。

### Decision 3: `outline_section` 包含完整 section 标记

**选择**：Celery 构建 `outline_section` 时包含 `## 写作大纲` 标题和约束语，模板只放 `{{outline_section}}`。

```
# Celery 构建:
outline_section = "## 写作大纲\n1. 要点\n2. 要点\n\n请严格按照以上大纲逐段写作。\n"
# 或为空:
outline_section = ""
```

**原因**：无大纲时渲染为空，不残留空标题。模板更简洁。

### Decision 4: `hotspot_title` → `topic`

**选择**：Celery 参数、variables key、模板占位符全部改为 `topic`。

**原因**：创建流程中该值是用户自拟标题，热点流程中是 `hotspot.title`。`topic` 同时覆盖两种语义。

### Decision 5: Humanize 接收 outline_section

**选择**：`trigger_humanize` 在 variables 中新增 `outline_section`，humanize 模板新增 `{{outline_section}}` 占位符。

**原因**：去 AI 味重写时，LLM 需要知道原文的结构约束，否则可能打散大纲结构。

## Risks / Trade-offs

- [Risk] 现有 seed_providers.py 中的 generate 模板被替换后，旧 seed 数据仍保留旧模板 → **Mitigation**：需手动更新数据库中已有的 scenario_configs 记录，或在 seed 脚本中增加 UPDATE 逻辑
- [Risk] `topic` 改名后，其他可能引用 `hotspot_title` 的代码（如 generation_logs、监控）被遗漏 → **Mitigation**：grep 全项目确认无残留引用
- [Risk] 前端 outline 改为可选后，旧测试用例可能依赖 outline 存在 → **Mitigation**：同步更新 e2e 测试
- [Trade-off] System Prompt 变长，增加 token 消耗 → 实际变化不大（原来 User Message 也很长），合并后反而消除重复注入的 `hotspot_title`
