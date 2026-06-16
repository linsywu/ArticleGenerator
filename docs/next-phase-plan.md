# 下一阶段改造计划

> 调研日期：2026-06-16 | 状态：待确认

---

## 1. 场景配置增强（提示词管理 + 排序 + 说明）

**现状问题：**
- `system_prompt_template` 只在编辑弹窗中可见，表格列表看不到提示词内容
- 没有"当前使用哪个提示词"的概念——同一场景只有一个配置
- 没有 `description` 字段说明每个场景的作用
- 没有 `sort_order` 字段，列表按 `id` 排序，运营者不清楚各场景的执行顺序

**改造方案：**

### DB
- `scenario_configs` 表新增：
  - `description` TEXT — 场景说明（如"文章生成时调用，根据热点标题和风格画像生成全文"）
  - `sort_order` INT DEFAULT 0 — 显示排序

### 后端
- Model + Schema 新增 `description`、`sort_order`
- API 列表接口按 `sort_order, id` 排序
- 新增 `POST /scenario-configs/{id}/activate` — 将同场景其他配置的 `enabled` 设为 0，激活当前（实现"切换使用哪个"）

### 前端
- 表格列新增"描述"列，显示 `description`
- 表格列新增"提示词预览"列（截断显示前 80 字）
- 支持同一场景多个配置（如 generate 可建多个模板），通过 `enabled` 切换当前激活

### 场景说明文案（建议种子数据更新）

| scenario | description | sort_order |
|----------|-------------|------------|
| distill | ① 风格蒸馏：分析参考文章，提取7维度结构化风格画像 | 1 |
| generate | ② 文章生成：根据热点/想法 + 风格画像 + 大纲生成全文 | 2 |
| humanize | ③ 去AI味：重写文章，消除AI写作痕迹，增加人味儿 | 3 |
| quality_review | ④ 质量评审：从原创性、逻辑、可读性、信息密度四个维度评分 | 4 |
| compliance_review | ⑤ 合规评审：检查政治敏感、色情、暴力、虚假信息、侵权风险 | 5 |
| refine | ⑥ 微调重写：根据修改关键词调整文章风格/语气/侧重点 | 6 |
| direction | ⑦ 方向生成：根据想法和账号风格，生成3-5个切入角度 | 7 |
| outline | ⑧ 大纲生成：根据想法+方向+风格，生成5-8个要点大纲 | 8 |

---

## 2. 文章标题字段 + 列表展示

**现状问题：**
- `articles` 表没有 `title` 列
- 评审列表、发布列表、任务记录都用 `hotspot.title` 代替文章标题
- 如果文章是自定义主题（非热点），标题列显示 `-`

**改造方案：**

### DB
- `articles` 表新增 `title` VARCHAR(200)

### 后端
- Article Model + Schema 新增 `title`
- `trigger_generate` 任务：生成文章后调用 title 提取/生成逻辑（或在 prompt 中要求 LLM 在文章开头输出标题）
- 或更简单：LLM 生成时要求标题放在第一行，后端解析提取

### 前端
- `Article` 接口新增 `title`
- ReviewView.vue：`row.title || row.hotspot?.title || "-"`
- PublishView.vue：同上
- TasksView.vue：同上

---

## 3. 文章标题生成步骤（创作流程）

**现状问题：**
- CreateView 5 步流程中没有标题生成环节
- 文章只有一个 `content` 字段，没有独立标题

**改造方案：**

在"确认大纲"（步骤 4）和"生成全文"（步骤 5）之间插入：

### 新增步骤：生成标题（步骤 4.5）

流程变为 6 步：
1. 选择账号
2. 输入想法 → 生成方向
3. 选择写作方向 → 生成大纲
4. 确认大纲 → **生成候选标题**
5. 选择/编辑标题 → 生成全文
6. 预览全文 → 提交评审

### 后端
- 新增 `trigger_title_generation` Celery 任务（调用 LLM scenario: `title`）
- 新增 `POST /generate/titles` 端点
- 新增 `TitleRequest` / `TitleResponse` schema
- 新增 `title` scenario_config（种子数据）

### 前端
- CreateView 新增标题生成步骤：显示 3-5 个候选标题 → 可编辑 → 选中 → 下一步

### 依赖
- 需要 Issue 2（文章 title 列）先完成

---

## 4. 统一任务中心（替代分散轮询）

**现状问题：**
- 文章生成（CreateView / GenerateView）和文章微调（ReviewView 弹窗）各自轮询，逻辑分散
- 微调点击后弹窗等待，无进度反馈，用户不知道任务在干嘛
- 没有全局视角看到"当前系统在跑什么任务"
- 如果有多个任务同时执行（生成 + 微调 + 蒸馏），用户完全不知道

**改造方案：统一任务中心**

核心理念：所有异步任务（生成、微调、蒸馏、人化、方向、大纲…）触发后进入任务中心，不再各自轮询。

### 全局入口

页面头部（App.vue 导航栏）增加任务中心入口：

```
┌──────────────────────────────────────────────────┐
│  ArticleGenerator    [热点] [任务] ...    🔔 3   │
└──────────────────────────────────────────────────┘
                                              │
                                              └─ 任务运行中数量 badge
                                              └─ 点击进入任务中心页
```

hover 时显示下拉卡片，列出最新 3 条运行中/最近完成的任务摘要。

### 任务中心页面 `/tasks-center`

卡片堆栈布局，按状态分组：

```
┌─ 进行中 (2) ──────────────────────────────────────┐
│ ┌─────────────────────────────────────────────┐   │
│ │ ✏️ 文章生成                    ⏳ 运行中 45s │   │
│ │ 热点：AI 编程工具焦虑                        │   │
│ │ 账号：开心的小溪 · 公众号                    │   │
│ │ ████████████░░░░░░░░ 估算中...               │   │
│ └─────────────────────────────────────────────┘   │
│ ┌─────────────────────────────────────────────┐   │
│ │ 🔧 微调重写                    ⏳ 运行中 12s │   │
│ │ 文章：#12 AI 写作工具对比...                  │   │
│ │ 关键词：语气更温和、增加案例                  │   │
│ │ ████████░░░░░░░░░░░░ 估算中...               │   │
│ └─────────────────────────────────────────────┘   │
├─ 等待中 (1) ──────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐   │
│ │ 📝 去AI味                      🕐 排队中     │   │
│ │ 文章：#11 测试文章...                         │   │
│ └─────────────────────────────────────────────┘   │
├─ 已完成 (12) ─────────────────────────────────────┤
│ ...折叠或分页...                                  │
└──────────────────────────────────────────────────┘
```

### 卡片信息

| 字段 | 说明 |
|------|------|
| 任务类型图标 | 生成 ✏️ / 微调 🔧 / 去AI味 📝 / 蒸馏 🧪 / 方向 💡 / 大纲 📋 / 评审 ✅ |
| 任务目标 | 文章标题 / 热点标题 / 账号名 |
| 状态标签 | 排队中 → 运行中 → 成功 / 失败 |
| 已用时间 | 实时更新的计时器（运行中的任务） |
| 附加信息 | 账号名、关键词、错误信息等 |

**注意：不显示百分比进度条**（Celery 不提供真实进度），改为显示"运行中 · 已用 XX 秒"，避免假进度条误导用户。

### 后端

#### 统一任务查询端点

```
GET /api/tasks/unified?status=running,pending&limit=20
```

返回合并后的任务列表，数据来源：
- `generation_tasks` 表（生成任务）
- `refine_tasks` 表（微调任务）
- 未来可扩展其他任务类型

统一响应格式：
```json
{
  "tasks": [
    {
      "id": 1,
      "task_id": "uuid",
      "task_type": "generate",      // generate | refine | humanize | distill | direction | outline | quality_review | compliance_review
      "status": "running",          // pending | running | success | failed | cancelled
      "target": "AI 编程工具焦虑",   // 任务目标描述
      "target_id": 5,               // 关联的文章/hotspot ID
      "account_name": "开心的小溪",
      "extra_info": "公众号",        // 附加信息
      "error_message": null,
      "created_at": "2026-06-16T10:00:00",
      "updated_at": "2026-06-16T10:00:45"
    }
  ],
  "running_count": 2,
  "pending_count": 1
}
```

#### Celery 任务增强
- 每个任务创建时在 `generation_tasks` / `refine_tasks` 表中写入 `target_description` 字段
- 或：通过 JOIN 关联获取目标信息

### DB（最小改动）
- `generation_tasks` 表新增 `task_type` VARCHAR(30) DEFAULT 'generate'（为统一查询预留）
- `refine_tasks` 表新增 `task_type` VARCHAR(30) DEFAULT 'refine'
- 两个表可选新增 `target_description` VARCHAR(200)

### 前端改动

| 文件 | 改动 |
|------|------|
| `App.vue` 或布局组件 | 头部新增任务入口按钮 + badge 计数 + hover 下拉 |
| 新建 `TaskCenterView.vue` | 任务中心页面，卡片堆栈布局 |
| `router/index.ts` | 新增路由 `/tasks-center` |
| `ReviewView.vue` | 微调触发后不弹等待框，改为 Toast "已加入任务中心" + 跳转入口 |
| `CreateView.vue` | 生成触发后同上，不再内联轮询 |
| `GenerateView.vue` | 批量生成触发后同上 |

### 轮询策略

任务中心页面统一轮询（`setInterval` 每 3 秒一次），只查询 `status IN (pending, running)` 的任务。页面离开时停止轮询。任务全部完成时自动停止。

### 与现有 TasksView 的关系

现有 `TasksView.vue`（`/tasks`）是旧的生成任务列表。改造后：
- 旧 `/tasks` 路由重定向到 `/tasks-center`
- 或保留 `/tasks` 作为简化版，`/tasks-center` 作为新版

---

## 5. 质量/合规评审结果缺失

**现状根因：**
- `humanize` 场景配置缺失（seed_providers.py 没有 seed，数据库里也没有）
- 调用链：`trigger_generate` 成功 → `trigger_humanize` → 查不到 humanize 配置 → 报错 → `except` 块中仍然调 `trigger_quality_review` + `trigger_compliance_review`
- 所以评审实际是跑了的，但 **humanize 步骤静默失败了**

**修复方案：**

### 立即修复（最小改动）
- 在 seed_providers.py 中补充 `humanize` 场景的种子数据
- 或在管理后台手动创建 `humanize` 场景配置

### humanize 种子配置
```
scenario: humanize
model: deepseek-v4-pro
priority: 5
system_prompt_template: (当前 tasks.py 第 169 行实际使用的场景名)
```

### 验证
- 生成一篇文章 → 检查 Celery 日志确认 humanize → quality_review → compliance_review 全部执行
- 检查 `articles` 表的 `quality_score`、`compliance_score`、`review_notes` 是否有值

---

## 6. 场景配置排序 + 说明

**与 Issue 1 合并实施**，参见上方第 1 项的完整方案。

---

## 实施优先级建议

| 优先级 | Issue | 原因 |
|--------|-------|------|
| **P0** | #5 评审结果缺失 | Bug——humanize 配置缺失导致调用链静默失败 |
| **P1** | #2 文章标题字段 | 多个页面展示缺陷，且是 #3 的前置依赖 |
| **P1** | #4 统一任务中心 | 全局任务可见性，替代分散轮询，涉及新页面 |
| **P2** | #3 标题生成步骤 | 新功能，依赖 #2 |
| **P2** | #1+#6 场景配置增强 | 提示词管理 + 排序 + 说明 |

---

## 预估改动范围

| Issue | DB | 后端 | 前端 | 风险 |
|-------|-----|------|------|------|
| #5 评审修复 | 无 | seed_providers.py（1 文件） | 无 | 低 |
| #2 标题字段 | ALTER TABLE articles | Model+Schema+API+Tasks | 3 个 View | 低 |
| #4 任务中心 | 2 表各加 1-2 列 | 新增统一查询 API | 新页面 + App.vue + 改 3 个 View | 中高 |
| #3 标题生成 | 无（依赖#2） | 新增 Task+API+Schema+Seed | CreateView.vue | 中 |
| #1+#6 场景增强 | ALTER TABLE scenario_configs | Model+Schema+API+Seed | ScenarioConfigsView | 中 |
