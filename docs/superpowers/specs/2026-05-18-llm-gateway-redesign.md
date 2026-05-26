# LLMService 通用网关改造 + 风格蒸馏系统设计

日期：2026-05-18 | 状态：待评审

---

## 一、目标

将 ArticleGenerator 的 LLMService 从"本地模型 + LoRA 微调"架构改造为"多 API 供应商网关 + Prompt 风格蒸馏"架构。核心目标：

- 批量参考不同赛道头部作者的文章，蒸馏出风格提示词
- 使用风格提示词 + 热点/话题生成高质量文章
- 接入多个 API 供应商，按场景路由，成本与质量可调

---

## 二、核心决策

| 决策 | 选择 |
|------|------|
| 风格控制方式 | 废弃 LoRA，采用 Prompt 风格蒸馏（few-shot 分析 → 结构化画像 → System Prompt） |
| 风格蒸馏策略 | 一次性蒸馏：所有参考文章参与分析 → 产出结构化风格画像文本 |
| 日常生成策略 | 风格画像作为 System Prompt，低成本批量生成（C 路径 few-shot 作为质量兜底） |
| API 供应商管理 | 管理后台统一配置 Provider（API Key + 模型列表） |
| 场景路由 | 蒸馏 / 生成 / 质量评审 / 合规评审 / 微调 分别配置供应商和模型 |
| 参考文章输入 | 链接自动解析优先，手动粘贴兜底 |
| 质量+合规评审 | 纯 AI 自动评审，生成后立即触发，结果展示在评审页辅助决策 |
| few-shot 文章选择 | 语义匹配（embedding 相似度）+ 代表篇标记 |

---

## 三、数据模型

### 新增表

**providers — API 供应商**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| name | VARCHAR(100) | Anthropic / DeepSeek / OpenAI |
| base_url | VARCHAR(500) | API 地址 |
| api_key | VARCHAR(500) | 加密存储 |
| models | JSON | `[{"name":"claude-opus-4-7","max_tokens":200000}]` |
| enabled | BOOLEAN | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

**scenario_configs — 场景路由**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| scenario | VARCHAR(50) | distill / generate / quality_review / compliance_review / refine |
| provider_id | FK → providers | |
| model | VARCHAR(100) | 具体模型名 |
| system_prompt_template | TEXT | 含 `{{变量}}` 占位 |
| params | JSON | temperature, max_tokens 等默认参数 |
| priority | INTEGER | 同一场景多 provider 的 fallback 顺序 |
| enabled | BOOLEAN | |

**reference_articles — 账号参考文章**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| account_id | FK → accounts | |
| title | VARCHAR(500) | |
| content | LONGTEXT | |
| source_url | VARCHAR(1000) | 来源链接 |
| embedding | JSON/BLOB | 文章 embedding 向量 |
| is_benchmark | BOOLEAN | 是否代表篇 |
| created_at | DATETIME | |

**generation_logs — 调用日志**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| scenario | VARCHAR(50) | |
| provider_id | FK | |
| model | VARCHAR(100) | |
| prompt_tokens | INTEGER | |
| completion_tokens | INTEGER | |
| latency_ms | INTEGER | |
| status | VARCHAR(20) | success / failed |
| error_message | TEXT | |
| created_at | DATETIME | |

### 变更表

**accounts — 新增字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| style_profile | TEXT | 风格画像文本 |
| style_profile_updated_at | DATETIME | |

**articles — 新增字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| quality_score | INTEGER | 0-100 |
| compliance_score | INTEGER | 0-100 |
| review_notes | TEXT | 评审备注（风险标签等） |

**accounts — 废弃字段**

- `lora_path`：保留列但不再使用，兼容已有数据

---

## 四、LLMService 网关架构

### 统一入口

```
POST /chat
{
  "scenario": "generate",
  "account_id": 1,
  "variables": { "hotspot_title": "...", "keywords": "..." },
  "extra_messages": []
}
```

### 处理流程

1. `scenario` → 查 `scenario_configs` → 得 template, provider_id, model, params
2. `account_id` → 查 `accounts.style_profile` → 注入 `{{style_profile}}`
3. `variables` → 渲染所有占位符
4. `provider_id` → 查 `providers` → 得 api_key, base_url
5. 拼装 messages → 对应 Adapter 调用 API
6. 记录 `generation_logs` → 返回统一响应

### Provider 适配层

```
BaseAdapter (抽象)
  └─ AnthropicAdapter  (Messages API, system 独立参数)
  └─ DeepSeekAdapter   (Chat Completions API, system 是 message 之一)
  └─ OpenAIAdapter     (Chat Completions API)
```

新增 Provider：实现一个 Adapter + 数据库 `providers` 表加一行。

### Prompt 模板示例

**distill:**
```
你是一位写作风格分析专家。以下是一位作者的{num_articles}篇代表文章：
{articles_content}
请分析这位作者的写作风格，输出结构化风格画像：
1. 语气特征 2. 句式习惯 3. 词汇偏好 4. 文章结构模式 5. 读者互动方式
```

**generate:**
```
{{style_profile}}

请严格遵循上述风格特征，根据以下热点撰写一篇完整文章：
热点：{{hotspot_title}}
```

**quality_review:**
```
请从以下维度评分（0-100）：结构清晰度、论点深度、语言流畅度、读者吸引力。
文章：{{article_content}}
```

**compliance_review:**
```
请检查文章是否存在：敏感政治内容、不实信息陈述、广告法违规用语。
标记风险项，无风险标记 safe。
文章：{{article_content}}
```

---

## 五、后端 API 扩展

### 新增路由

| 路由 | 方法 | 职责 |
|------|------|------|
| `/api/providers` | CRUD | 供应商管理 |
| `/api/scenario-configs` | CRUD | 场景路由配置 |
| `/api/accounts/{id}/reference-articles` | CRUD | 参考文章管理 |
| `/api/accounts/{id}/distill` | POST | 触发风格蒸馏任务 |
| `/api/chat` | POST | 转发至 LLMService，后端内部调用 |

### Celery 任务（5 种）

| 任务 | 场景 | 说明 |
|------|------|------|
| `trigger_distill` | distill | 参考文章 → style_profile |
| `trigger_generate` | generate | 热点 + style_profile → 文章 |
| `trigger_quality_review` | quality_review | 文章 → 质量评分 |
| `trigger_compliance_review` | compliance_review | 文章 → 合规评分 |
| `trigger_refine` | refine | 原文 + 关键词 → 重写 |

### 生成流程时序

```
1. trigger_generate → 文章写入 articles
2. 成功后自动 chain → trigger_quality_review
3. 成功后自动 chain → trigger_compliance_review
4. 三项全部完成 → generation_tasks 状态标记 success
```

---

## 六、前端改造

### 新增页面

**`/providers`** — 供应商管理：增删改查、API Key（加密显示）、模型列表维护

**`/scenario-configs`** — 场景配置：每场景选 Provider + Model、编辑 Prompt 模板、设置默认参数

### 改造页面

**`/accounts`** — 新增三个区域：
- 参考文章列表（添加文章弹窗：粘贴链接 → 自动抓取 / 手动粘贴 → 标记代表篇）
- 风格画像展示（蒸馏状态、画像文本预览、重新蒸馏）
- 废弃 lora_path 展示

**`/review`** — 评审列表新增评分/风险标签列；详情展开显示维度分值和风险标记

### 不变页面

`/`（热点列表）、`/tasks`（任务列表）、`/publish`（待发布）、`/hotspot-sources`（热点源管理）

---

## 七、迁移路径

### 阶段 1：数据库迁移
- 执行 migration 003：新建 4 张表，alter 2 张表
- 已有数据不受影响

### 阶段 2：LLMService 改造
- 重写 gateway + adapter 层
- 删除 model_loader.py
- 更新 requirements.txt（移除 torch/transformers/peft，添加 anthropic/openai SDK）

### 阶段 3：后端 API 扩展
- 新增路由 + Celery 任务
- 改造 generate 流程（自动 chain 评审）

### 阶段 4：前端改造
- 新增 2 个页面，改造 2 个页面

### 阶段 5：配置初始化
- 在管理后台添加至少 1 个 Provider（如 DeepSeek）
- 配置 5 个场景路由
- 为已有账号导入参考文章、触发蒸馏

### 向后兼容
- `accounts.lora_path` 保留不删
- Docker Compose 编排结构不变
- HotspotCrawler 完全不动
- 已有 API 端点保持可用（废弃的返回空实现）

---

## 八、风险与对策

| 风险 | 对策 |
|------|------|
| 蒸馏后风格画像与原文风格偏差大 | 蒸馏结果可人工编辑；支持重新蒸馏 |
| 链接解析失败率高 | 手动粘贴作为兜底输入 |
| 质量/合规评审误判 | 评分仅作辅助参考，最终决策权在运营人员 |
| API 供应商不稳定 | Provider 表支持同场景配置多个 fallback（priority 字段） |
| 大批量生成时 API 成本陡增 | 场景路由控制成本敏感场景走便宜模型 |
