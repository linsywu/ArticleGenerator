# 文章创作流程改造设计

- 日期：2026-07-07
- 状态：已批准，待制定实现计划
- 关联：承接「风格蒸馏质量重构」（2026-07-06），蒸馏产物已切换为 `style_profile`（指南）+ `style_features`（证据清单）

## 背景与问题

风格蒸馏重构完成后，下游文章创作流程暴露 4 个问题：

1. **style 注入疑似异常**：用户反馈「文章生成提示词未加入 style_feature，且仍残留 style_instructions」。
2. **四场景提示词薄弱**：direction / outline / title / generate 的提示词不足以指导生成高质量文章。
3. **去 AI 味等于重写**：humanize 步骤把整篇文章覆盖重写，偏离「轻度润色」初衷。
4. **质量评审无意义**：评审只给泛泛总分，无法定位低质量段落，也无法指导微调。

## 现状调研结论

### 问题 1：style 注入（部分判断与代码不符）

- `style_instructions` **实际已完全清除**：`019` 迁移已移除，DB 中全部 10 个场景模板均不含 `{{style_instructions}}`，代码仅在测试中作为「不应出现」的断言。
- `style_features` **设计上不注入**：`models.py:62` 注释「仅展示/审计用，不注入生成」，`gateway.py:67-74` 仅注入 `style_profile`。features 是带原文引证的证据清单（长、偏分析），`style_profile` 是从它凝练的可模仿指南，后者才适合喂给生成。
- 四场景（generate/direction/outline/title）模板均含 `{{style_profile}}`，`tasks.py` 均传 `account_id`，注入链路畅通。

### 问题 2：四场景提示词薄弱（DB 原文核对）

| 场景 | 现状 | 薄弱点 |
|------|------|--------|
| direction | 5 行 | 无多样性约束、无 few-shot、未深度利用风格 |
| outline | 4 行 | 无结构指引、无字数分配、未要求紧扣方向 |
| title | 4 条要求 | 无 few-shot、未利用风格标题样板 |
| generate | 019 重写过，最完善 | 实际模板无禁用词清单（LLMService CLAUDE.md 声称有但 DB 没有）、无 few-shot |

### 问题 3：humanize 像「重新生成」（根因）

- 提示词接收整篇 `article_content` 并输出整篇 → 天然倾向重写；
- 第 4 条「加入个人化观点和感受」鼓励 LLM 增添新内容、偏离原意；
- 无「保持原意/不增删/保持段落结构」约束，`temperature=0.7` 偏高；
- `trigger_generate` 生成后**立即同步 humanize 并覆盖 content**（`tasks.py:206-228`），用户从未看到 generate 原文。
- `trigger_humanize` 无 API 调用方、前端无 humanize 入口，删除安全。

### 问题 4：质量评审无意义（根因 + 链路断裂）

- 评审只输出总分 + 泛泛理由，**不定位段落**；
- `max_tokens=1024`（已知会截断，需 4096）；
- 结果存 `review_notes` 纯文本，非结构化；
- **关键断链**：`refine` 只接收人工 `keywords`（`tasks.py:319`），完全不消费 quality_review 输出。

## 设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| humanize 去留 | **删除场景，去 AI 味并入 generate** | 砍掉二次重写，成本减半；generate 直出终稿 |
| 评审 + 微调 | **段落级结构化 + 接入 refine** | 打通「评审→微调」闭环，实现「评审指导重写」 |
| style_features 注入 | **维持现状（不注入）** | features 是分析性证据，注入干扰生成、增 token |
| refine 接入方式 | **自动带入评审建议，手填关键词可选** | 保留用户控制权，改动小，无新按钮 |

## 新流程

```
旧: generate → humanize(覆盖) → quality_review(总分) → compliance_review
新: generate(内嵌反AI味) → quality_review(段落级JSON) → compliance_review
                                          ↓
                                    refine(自动消费评审建议)
```

## 模块设计

### 模块 A：拆除 humanize，去 AI 味并入 generate

**代码清理**（`app/tasks.py`）：
- 删除 `trigger_generate` 内同步 humanize 调用（`tasks.py:206-228`）；生成完直接落库，不再被覆盖。
- 删除 `trigger_humanize` 任务（已确认无 API 调用方、前端无入口）。
- `trigger_generate` 末尾 quality/compliance 触发改为基于 generate 原文 `content`。

**DB**：`DELETE FROM scenario_configs WHERE scenario='humanize'`（用户已授权删除）。

**generate 提示词内嵌反 AI 味**（与模块 B 的 generate 部分合并）：
- 内嵌禁用词清单：`总的来说 / 综上所述 / 首先其次最后 / 换言之 / 从某种程度上 / 随着 / 在当前`。
- 反 AI 痕迹具体要求：口语化、段落长短错落、避免套路连接词、避免三段式对称。
- **禁用词维护方式**：写入 generate 场景模板（DB），后续通过场景配置 UI 或新迁移增删，无需改代码。

### 模块 B：四场景提示词增强

每场景补三件事：**结构约束 + few-shot/范例 + 深度利用 style_profile**。

| 场景 | 增强方向 |
|------|---------|
| direction | ① 强制「每个方向必须是不同切入角度」，给出角度类型清单（情感共鸣/利益驱动/反常识/实用干货/故事叙事）② 结合账号风格画像的思维模式 ③ 输出强约束 JSON |
| outline | ① 结构框架（问题引入→分析→方案→升华，或起承转合）② 每要点标注字数占比 ③ 紧扣选定 direction ④ 输出 JSON 数组 |
| title | ① few-shot（好/坏标题对比）② 利用 style_profile 标题样板 ③ 输出纯字符串数组 |
| generate | ① 内嵌禁用词清单 ② 反 AI 痕迹具体要求 ③ 保留现有「核心约束 + 硬性要求」骨架 |

### 模块 C：质量评审段落级结构化

**输出格式**（quality_review 提示词要求输出 JSON）：
```json
{
  "overall_score": 85,
  "dimensions": {"originality": 22, "logic": 21, "readability": 22, "info_density": 20},
  "weak_paragraphs": [
    {"index": 3, "severity": "high", "issue": "套话堆砌，信息密度低",
     "suggestion": "用具体数据替换「随着时代发展」类空话"}
  ]
}
```

- **段落定位**：提示词要求 LLM 按自然段落（空行分隔）从 1 编号（跳过标题），仅输出 severity=high/medium 的问题段落 + 改进建议。
- **max_tokens**：`1024 → 4096`。
- **存储**：`articles` 表新增 `quality_review_detail TEXT`（JSON）；`quality_score` 存总分；`review_notes` 留给合规。
- **解析**：`trigger_quality_review` 先提取 JSON 块取 `overall_score`，失败回退 `_parse_score`（容错）。
- **前端**：评审展示从「总分+文本」升级为「总分 + 四维分 + 段落问题清单」。
- 合规评审**不动**。

### 模块 D：refine 自动带入评审建议

**`trigger_refine` 改造**（`app/tasks.py`）：
- 开头读取 `article.quality_review_detail`，解析 `weak_paragraphs`，格式化为文本注入新变量 `review_suggestions`。
- 无评审/全绿时该变量为空，refine 正常按关键词工作（向后兼容）。

**refine 场景模板**加 `{{review_suggestions}}`：
```
## 质量评审发现的问题段落（优先修复，保持其他段落不变）
{{review_suggestions}}

## 用户修改关键词（可选）
{{keywords}}

原文：
{{article_content}}
```

**前端**：微调对话框加一行提示「系统已自动带入质量评审建议，你可补充修改关键词」。

## 改动清单

### 迁移脚本（`ArticleGeneratorDatabase/migrations/`）

| 脚本 | 内容 |
|------|------|
| `022_update_generation_prompts.sql` | UPDATE direction/outline/title/generate/quality_review/refine 六场景模板；DELETE humanize 场景 |
| `023_add_quality_review_detail.sql` | `ALTER TABLE articles ADD COLUMN quality_review_detail TEXT` |

### 后端（`ArticleGeneratorService/`）

| 文件 | 改动 |
|------|------|
| `app/tasks.py` | 删 `trigger_humanize`；`trigger_generate` 删同步 humanize、评审基于原文；`trigger_quality_review` 改 JSON 解析+存 detail；`trigger_refine` 注入 review_suggestions |
| `app/models.py` | `Article` 加 `quality_review_detail` |
| `app/schemas.py` | Article 响应加 `quality_review_detail`；refine 请求不变 |

### 前端（`ArticleGeneratorAdm/`）

- 评审结果展示组件：总分+文本 → 总分+维度+段落清单。
- 微调对话框：加「已带入评审建议」提示。

### LLMService

无改动（gateway 注入逻辑不变）。

## 实施拆分

遵循 CLAUDE.md「逐项确认」，按依赖关系拆为 3 个独立 change，各自 spec → plan → 实现 → 验证 → 用户确认后再下一个：

| 顺序 | Change | 内容 | 迁移 | 依赖 |
|------|--------|------|------|------|
| 1 | 提示词重构 + 拆 humanize | 模块 A + B | 022 | 无 |
| 2 | 评审段落级结构化 | 模块 C | 023 | 无 |
| 3 | refine 接入评审 | 模块 D | （模板已在 022） | 依赖 2 的字段 |

> refine 场景模板更新放进 change 1 的 022（一次性改全场景），但 `trigger_refine` 代码改动放 change 3（依赖 change 2 字段先存在）。

## 非目标（YAGNI）

- 不改合规评审（用户明确抛开）。
- 不改 LLMService gateway 注入逻辑（已正常工作）。
- 不建独立的禁用词配置表（写入模板即可，YAGNI）。
- 不保留 humanize 历史数据（用户选择直接删）。
- style_features 继续仅展示用，不注入生成。
