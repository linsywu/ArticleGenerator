## Context

当前 `ArticleGeneratorService/app/tasks.py:98` 硬编码 `'字数1500左右。'`，所有文章生成统一使用该值。QQ 账号矩阵运营中，不同平台、不同账号对文章长度需求差异显著（如微博短文 500 字、知乎长文 3000+ 字），需要一个可配置的字数方案。

系统已有账号级配置能力（`style_profile`、`style_profile_structured`），字数配置可作为账号属性自然扩展。

## Goals / Non-Goals

**Goals:**
- 账号支持配置多档字数选项（value=label 格式，如 `1500=1500左右`）
- 账号支持设置默认字数，新建文章自动填充
- 文章创作流程"输入想法"步骤可选择字数，覆盖默认值
- 后端生成/微调任务将所选字数注入 LLM 提示词，替换硬编码

**Non-Goals:**
- 不修改 LLM 服务 `max_tokens` 动态计算（token 与字数映射关系复杂，后续迭代）
- 不修改热点批量生成流程（GenerateView.vue 热点多选直接生成，不走 CreateView 步骤）
- 不在 scenario_configs 中增加字数配置（字数属于账号属性，不是 Provider/Model 属性）

## Decisions

### 1. 数据存储：TEXT JSON vs 单独表

**选择**：`accounts` 表新增 2 个列
- `word_count_options` TEXT — JSON 字符串，如 `[{"value":"500","label":"500字"},{"value":"1500","label":"1500字左右"}]`
- `default_word_count` VARCHAR(20) — 默认选中值，如 `"1500"`

**备选**：单独建 `word_count_options` 表。不选的原因：账号级配置项很少超过 5 档，JSON 列足够轻量，避免额外 JOIN。

### 2. 前端字数选择器：自定义下拉 vs 预设档位

**选择**：纯从 `word_count_options` 读取选项渲染 el-select，不预设死档位。账号 A 可以配 `500/1000/1500`，账号 B 可以配 `1500/3000/5000`，完全灵活。

### 3. 字数注入方式：提示词变量 vs 独立参数

**选择**：通过 `variables` 注入到 LLM `/chat` 请求，在 `system_prompt_template` 中用 `{{word_count}}` 占位。当前 `tasks.py` 中硬编码 `'字数1500左右。'` 改为读取 `variables["word_count"]` 拼接。

这要求手动在管理后台的 generate/refine 场景配置里添加 `{{word_count}}` 占位（提示词末尾），作为一次性配置操作。

### 4. 向后兼容

- `word_count_options` 为空 → CreateView 不显示字数选择器，tasks.py 使用当前硬编码默认 "1500左右"
- `default_word_count` 为空 → 选择器不预选，用户手动选或留空
- 既有的 GenerateView（热点批量生成）传入 `word_count=None`，后端保持现有行为

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 新增 DB 列后旧数据无默认值 | 字段 nullable，代码中 `or "1500左右"` 兜底 |
| system_prompt_template 忘记加 `{{word_count}}` | 占位空值时不注入额外字数要求，文章仍会生成但可能偏离预期 |
| 字数选项 JSON 格式出错 | Account API 不做严格校验，前端输入时提示格式 |

## Migration Plan

1. 新增 DB 迁移脚本（ALTER TABLE accounts ADD COLUMN）
2. 部署后端代码（schema + API + tasks）
3. 部署前端代码
4. 在管理后台更新 generate/refine 的 system_prompt_template，末尾加 `{{word_count}}`
5. 为已有账号配置字数选项

回滚：删除新增列 + 回滚代码即可，无数据丢失风险。
