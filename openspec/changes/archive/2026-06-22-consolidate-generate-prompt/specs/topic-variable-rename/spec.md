## ADDED Requirements

### Requirement: Variable renamed from hotspot_title to topic
所有涉及文章主题的变量 SHALL 使用 `topic` 替代 `hotspot_title`。此变更覆盖 Celery 任务参数、API 请求体、Gateway variables、System Prompt 模板占位符、以及 LLM 服务端点。

#### Scenario: Celery task uses topic parameter
- **WHEN** `trigger_generate` 被调用
- **THEN** 第一个位置参数 SHALL 命名为 `topic`（原 `hotspot_title`）

#### Scenario: API payload carries topic
- **WHEN** Celery 任务向 LLM 服务发送 generate 请求
- **THEN** 请求体 variables SHALL 包含 `"topic"` key（原 `"hotspot_title"` key）

#### Scenario: Template uses topic placeholder
- **WHEN** generate 场景的 system_prompt_template 引用文章主题
- **THEN** SHALL 使用 `{{topic}}` 占位符（原 `{{hotspot_title}}`）

#### Scenario: Template label matches semantics
- **WHEN** 模板中标注文章主题
- **THEN** SHALL 使用 `文章主题` 标签（原 `热点标题`），语义覆盖热点和自定义两种来源

### Requirement: Backward compatibility for /generate endpoint
LLM 服务的 `/generate` 端点 SHALL 继续接受 `hotspot_title` 字段但内部转为 `topic`，保证热点流程不受影响。

#### Scenario: Hotspot flow still works
- **WHEN** 热点流程调用 `/generate` 端点
- **THEN** `hotspot.title` SHALL 作为 `topic` 的值传递给 Gateway，生成行为不变
