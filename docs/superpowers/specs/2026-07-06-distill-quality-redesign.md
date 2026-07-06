# 风格蒸馏质量重构设计

**日期**: 2026-07-06
**状态**: 已确认，待实现
**关联**: 替代当前 `trigger_distill`（7 维度逐维蒸馏）实现

## 背景与问题

当前风格蒸馏（`trigger_distill`）把账号参考文章按 7 个固定维度（思维模式/结构/句式/词汇/论据/禁忌/留白）逐维度调用 LLM 提炼，产出指令式风格画像注入到 `{{style_profile}}` 指导生成。

**核心问题：蒸馏输出太泛、千篇一律。** 以"陆拾一"账号（14 篇参考文章，已蒸馏 9 次）的实际输出为例，大量内容是通用写作建议（"应优先使用短句""多采用排比和反问"），换账号产出的画像高度相似，没抓到作者独有特征。

### 根因

当前 distill 模板（`scripts/seed_providers.py` distill scenario）的四个设计合力把输出推向套话：

| 设计 | 后果 |
|------|------|
| "用指令式语气：应.../避免..." | LLM 产出通用写作建议而非观察性特征 |
| "每条不超过 40 字" | 40 字装不下具体例证，被迫抽象化 |
| 无 few-shot、无对比基准 | LLM 不知"具体"长什么样、"独特"相对什么而言 |
| 每篇硬截断到 800 字 | 陆拾一平均 2672 字，丢 70%，标志特征可能在截断段 |

一句话：**问的是抽象问题，自然得到抽象答案。**

## 目标

让蒸馏产出**带原文引证、抓作者独有特征、跨垂类自适应**的风格指南，使生成模型能据此真正模仿该作者。

**非目标**: 不改动生成流程本身（generate/humanize/review 不变），不改方向/大纲/标题的生成逻辑（仅清理冗余注入代码）。

## 方案：两阶段蒸馏 + 整段注入（B+C）

### 整体架构

```
Stage 1 · 证据提取（temperature 0.2，重证据）
  输入: 该账号全部参考文章（智能压缩，非硬截断）
  LLM 任务:
    ① 自动判断作者类型/垂类（不预设）
    ② 在该类型内，提取标志性特征 —— 必须带原文逐字引用
  输出: "标志性特征清单"（带引证）

Stage 2 · 凝练成指南（temperature 0.5，重表达）
  输入: Stage 1 的特征清单
  LLM 任务: 凝练成连贯的"写作风格指南"，
            必须包含可模仿的具体范例
  输出: 写作风格指南文本块 → 存入 account.style_profile
```

**整段注入已端到端打通**：Gateway（`LLMService/app/gateway.py:68-72`）已按 `account_id` 自动把 `account.style_profile` 注入所有任务的 `{{style_profile}}` 占位符。direction/outline/title/generate 四个模板都已有该占位符。本次重构下游注入零改动。

### 多风格约束的处理

"不只蒸馏一种风格的作者"意味着不能硬编码垂类。三处改造：

| 设计点 | 处理 |
|--------|------|
| 差异化基准 | Stage 1 第一步自动定位作者类型，"独特"始终相对同类型而言 |
| few-shot | Stage 1 内嵌跨垂类对比示例（generic ❌ vs specific ✓），让 LLM 对任意垂类泛化 |
| 维度 | **完全由 LLM 自定**——作者最值得提炼什么就提炼什么，不套固定维度 |

## 详细设计

### Stage 1 Prompt（distill-extract 场景）

四条**硬性要求**，违反即判失败：

1. **每条特征必须附原文逐字引用**（用「」标出原句/原词），无引证不写
2. **不准写通用建议**——"应多用短句""应结构清晰"这类对任何作者都成立的话一律删除
3. **维度自定**——不套固定维度，由作者本身决定提炼什么
4. **宁少而准**（5-8 条带引证），不多而泛

工作流：先定位作者类型（"这位是 X 类，主流写法是..."）→ 再在同类内提取区别于主流的标志性特征。

输出示例（片段）：
```
作者类型：情感两性类 · 主流写法是过来人视角讲道理

标志性特征：
1. 设问式开头：「你有没有发现，越是懂事的女人，越没人疼？」
   ——几乎每篇都用反问设问开篇，制造代入感
2. 高频短句堆叠制造节奏：「他不爱你。他不心疼你。他只是习惯你。」
   ——情绪高点用 3-4 个独立短句连击
```

### Stage 2 Prompt（distill-synthesize 场景）

把特征清单凝练成 600-900 字《写作风格指南》，**强制保留四类可模仿样板**：

- 标志性开头范例（1-2 例，带原句）
- 标志性结尾范例（1-2 例，带原句）
- 高频标志词清单（具体词）
- 禁忌词/禁忌处理清单

指令必须由范例推出，用第二人称把范例嵌进指令："开头常用设问引入，如「你有没有发现...」"。

### 文章压缩策略（替代 800 字硬截断）

- **≤5 篇**：全文输入（claude-sonnet 200K 上下文足够）
- **6-15 篇**：每篇取"首段 + 中段抽样 + 尾段"，保留全文风格信号
- **>15 篇**：均匀抽样到 15 篇（首篇 + 末篇 + 中间均匀取样），保证覆盖作者早/中/近期风格

## 工程改动

### 改动文件清单

| 文件 | 改动 |
|------|------|
| `scripts/seed_providers.py` | 删除旧 `distill` scenario_config；新增 `distill-extract`（Stage 1）+ `distill-synthesize`（Stage 2），写入新 prompt + few-shot |
| `ArticleGeneratorService/app/tasks.py` · `trigger_distill` | 重写：2 次 LLM 调用替代 7 次；新文章压缩策略；落库整段指南到 `style_profile`；状态走 `extracting` → `synthesizing` → `ready` |
| `ArticleGeneratorService/app/tasks.py` · direction/outline/title | **删除冗余**：移除从 `style_profile_structured` 拉 `thinking_pattern`/`structure_pattern` 的代码（Gateway 已自动注入整段 `style_profile`） |
| `ArticleGeneratorService/app/api/distill.py` | status 端点不再解析 `structured._progress`，直接返回 status |
| `ArticleGeneratorService/app/models.py` | 移除 `style_profile_structured` 列 |
| `ArticleGeneratorService/app/schemas.py` | 移除 `style_profile_structured` 字段 + validator |
| `ArticleGeneratorAdm/src/components/accounts/DistillDialog.vue` | 展示从 `style_profile_structured`（7 维分块）→ `style_profile`（整段指南）；进度 UI 从 7 步维度 → 按 status 映射的 2 阶段；按钮判断条件改用 `style_profile` |
| `ArticleGeneratorAdm/src/api/client.ts` + `types.ts` | status 响应类型改 2 阶段；`Account` 类型移除 `style_profile_structured` 字段 |
| `ArticleGeneratorDatabase/migrations/020_drop_style_profile_structured.sql` | `ALTER TABLE accounts DROP COLUMN style_profile_structured` |

### 进度展示（不加新字段，编码进 status 枚举）

`style_profile_status` 值细化：

| status 值 | 含义 | 前端展示 |
|-----------|------|---------|
| `none` | 未蒸馏 | 开始蒸馏 |
| `extracting` | Stage 1 运行中 | "提取特征中… (1/2)" |
| `synthesizing` | Stage 2 运行中 | "凝练指南中… (2/2)" |
| `ready` | 完成 | 展示指南 + 重新蒸馏 |
| `failed` | 失败 | 报错 |

### 冗余清理

direction/outline/title 任务当前手动从 `style_profile_structured` 拉 `thinking_pattern`/`structure_pattern` 塞进 variables——这是冗余，Gateway 已按 account_id 注入整段 `style_profile`。删除后方向/大纲/标题生成由整段指南统一指导，行为更一致。

### 迁移与种子（已知陷阱）

按 [seed-providers-upsert-behavior] 记忆：UPSERT 不覆盖已有 scenario_config 的模板。处理：
- 种子脚本删除旧 `distill` scenario_config，新增 `distill-extract` + `distill-synthesize`
- 已有 dev DB：先 `DELETE FROM scenario_configs WHERE scenario='distill'` 再跑种子（dev 环境安全，只删配置不碰业务数据）
- `020_*.sql` 迁移 DROP COLUMN（SQLite 3.35+ 支持 `ALTER TABLE DROP COLUMN`）

## 测试计划

- `test_distill_task.py`：断言 2 次 LLM 调用、整段指南落库、引证存在、`style_profile_structured` 不再被写
- `test_distill_status.py`：进度结构改为 status 枚举断言（extracting/synthesizing/ready）
- direction/outline/title 测试：验证移除 structured 读取后仍正常（靠 Gateway 注入）
- **真实蒸馏验证**（按 [verification-rule]）：对陆拾一账号实际触发蒸馏，人工对比新旧 `style_profile`——新输出应带原文引证、不再有"应多用短句"这类套话、整段连贯可读

## 兼容性

- 现有账号的 `style_profile`（旧 7 维拼接文本）在新设计下仍可被 Gateway 注入，生成不受影响；重新蒸馏后覆盖为新格式指南
- `style_profile_structured` 列移除后，旧数据随之消失（可接受——该字段无外部消费者，仅 DistillDialog 展示，会改为展示 `style_profile`）
- 下游 generate/humanize/review 流程零改动
