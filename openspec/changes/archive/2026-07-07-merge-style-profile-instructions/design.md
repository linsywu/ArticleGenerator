## Context

当前架构中，账号风格画像以两种形式进入 generate prompt：

| 变量 | 来源 | 注入方式 |
|------|------|----------|
| `style_profile` | `account.style_profile` (Text) | LLM Gateway 自动补齐 |
| `style_instructions` | `account.style_profile_structured` (JSON) → `tasks.py` 拼接 | Celery 任务显式传参 |

两个变量覆盖同一份蒸馏结果的不同子集，导致 prompt 中风格信息重复出现。同时蒸馏 prompt 本身以"分析"为导向，产出的文本偏长且不适合直接作为写作指导。

蒸馏流程：Celery 任务串行调用 7 次 LLM（每次分析一个维度），结果存入 `style_profile_structured`（JSON），再拼接为 `style_profile`（文本摘要）。

## Goals / Non-Goals

**Goals:**
- 合并 `style_profile` 和 `style_instructions` 为单一变量 `style_profile`
- 优化 `distill` scenario 的 system_prompt_template，使每维度输出精炼的写作指导
- `style_profile` 文本汇总格式从"分析报告"转为"写作指导"
- 移除 `tasks.py` 中 `style_instructions` 的构建和传参逻辑

**Non-Goals:**
- 不改变 7 维度蒸馏架构（串行调用方式不变）
- 不改变 `style_profile_structured` JSON 字段结构
- 不改变 LLM Gateway 的变量注入逻辑
- 不添加新的蒸馏后处理步骤（如全局摘要 LLM 调用）

## Decisions

### Decision 1: 保留 `style_profile`，删除 `style_instructions`

**选择**：只保留 `style_profile`（Gateway 自动注入），删除 `style_instructions`。

**原因**：
- `style_profile` 覆盖全部 7 维度，`style_instructions` 仅覆盖 4 维度
- Gateway 已有自动注入逻辑，无需 tasks.py 重复传参
- 减少变量数量降低 prompt 维护复杂度

**替代方案**：只保留 `style_instructions`。否决原因：需要改 Gateway 注入逻辑，且仅 4 维度信息不完整。

### Decision 2: 重写 distill 模板，改为单维度通用模板

**选择**：重写 `distill` 场景的 `system_prompt_template` 为通用单维度分析模板，利用 `{{dimension}}` 和 `{{dimension_prompt}}` 变量动态适配不同维度。

**旧模板**（硬编码 7 维度，与 per-dimension 调用矛盾）：
```
分析以下参考文章，提炼出账号的写作风格画像。
分析维度：
1. 语气特点（正式/口语化/幽默/严肃等）
...
```

**新模板**（通用 + 写作指导输出）：
```
你是一个写作风格提炼师。根据以下参考文章，仅针对「{{dimension}}」维度提炼写作指导。

分析要点：{{dimension_prompt}}

要求：
- 输出 3-5 条写作指导指令，每条 15-30 字
- 用指令式语气：应... / 避免... / 倾向于... / 多...少...
- 不要写分析过程或原因解释
- 只写确定能观察到的特征，不要编造

共 {{num_articles}} 篇参考文章：
{{articles_content}}
```

**原因**：模板与 per-dimension 调用方式一致，输出格式约束为写作指导。

### Decision 3: 修改 `style_profile` 汇总格式

**选择**：将 `dim_labels` 改为"写作指导"风格的标签，整体格式更紧凑。

**旧格式**：
```
【思维特征】
<原始 LLM 输出>
【结构模式】
<原始 LLM 输出>
```

**新格式**：保持分段但标签改为指导性语言，段落间紧凑排列：
```
## 思维特征
<原始 LLM 输出>

## 结构模式
<原始 LLM 输出>
```

同时移除 `dim_labels` 中"分析"相关措辞。

### Decision 4: generate 模板中去掉 `{{style_instructions}}`

**选择**：从 generate 的 `system_prompt_template` 中移除 `{{style_instructions}}` 行，将 `{{style_profile}}` 的上下文描述从"风格参考"改为"写作风格要求（必须严格遵守）"。

## Risks / Trade-offs

- **蒸馏输出质量依赖 prompt 调优**：新 prompt 可能需要在测试中迭代。→ 先更新 seed，蒸馏测试账号验证输出质量
- **已有蒸馏数据不变**：已蒸馏账号的 `style_profile` 是旧格式文本，直到重新蒸馏才更新。→ 可接受，generate 仍能正常工作，只是旧格式偏长
