## Context

素材中心 → 文章 → 创作方向：用户点击后，前端写死 `account_id=0` 调 `POST /api/generate/directions`，Celery 任务调 LLMService `/chat`（scenario=`direction`）。当前 LLM 调用链路存在三个问题：

1. **无用户消息**：`gateway.py:85` 只把 `user_prompt`/`hotspot_title`/`keywords` 作为用户消息；direction 任务传的是 `idea`/`word_count`，不匹配 → LLM 只收 system prompt
2. **无格式约束**：prompt 模板未要求 JSON 输出，LLM 自由发挥
3. **解析器弱**：备用正则可匹配 `1. xxx`/`- xxx`，但不支持中文编号

三者叠加 + temperature=0.9 → 偶发解析失败 → `directions: []`。

## Goals / Non-Goals

**Goals:**
- 无论有无账号风格，direction 调用稳定返回可解析的方向列表
- LLM 输出格式可预测（JSON 优先 + 增强备用解析）
- system_prompt_template 在 `style_profile` 为空时不留空字段

**Non-Goals:**
- 不改前端调用方式（`account_id=0` 保持不变）
- 不改 LLMService gateway 的消息组装逻辑
- 不新增 API 接口

## Decisions

### 决策 1：通过 `user_prompt` 传用户消息（不改 gateway）

**选**：Celery 任务构建 `user_prompt` 字符串，含想法 + 字数 + 格式指令 + 可选风格提示。

**不选**：改 gateway 让 `idea` 也作为用户消息 → 影响所有场景，风险大。

**理由**：网关已有 `user_prompt` → 用户消息的通道，`distill` 场景刚修过同类问题（commit `e50b750`），复用同一模式。

### 决策 2：`user_prompt` 中要求 JSON 格式，prompt 模板保持简洁

**选**：在 `user_prompt` 末尾加 `请以JSON数组格式输出：[{"id": "A", "title": "..."}, ...]`。

**不选**：在 system_prompt_template 中要求 JSON → 用户编辑模板时容易丢失格式约束。

**理由**：格式指令属于"怎么输出"，放在 user prompt 中更合适；system prompt 只管"你是谁、做什么"。

### 决策 3：备用解析器增加中文格式支持

**选**：正则增加 `方向[一二三四五六七八九十]|角度\d+|[A-F][.、]` 等中文常见编号。

**不选**：重试调用 → 增加延迟和成本。

### 决策 4：prompt 模板中 `{{style_profile}}` 的处理

**选**：模板保持 `{{style_profile}}`，但当值为空时渲染为空字符串，不影响可读性。风格信息改在 `user_prompt` 中按需拼接。

**不选**：在模板中用条件判断 → 模板引擎不支持 Jinja2。

## Risks / Trade-offs

- [LLM 仍可能不按 JSON 格式输出] → 增强的备用解析器兜底；且 temperature 0.9 + 明确 JSON 指令后，不按格式的概率极低
- [备用解析可能误匹配] → 限制行首模式，误匹配概率低
- [模板需手动更新] → proposal 中提供完整模板文本，用户粘贴即可
