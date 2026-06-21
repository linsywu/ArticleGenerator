## Context

当前账号风格页面（`AccountsView.vue`，618 行）使用单一弹窗承载 4 个 Tab，所有逻辑耦合在一个文件中。蒸馏接口返回 Celery task_id 后前端不做任何跟踪。参考文章和风格画像的数据流是输入→输出的上下游关系，但在 UI 上被 Tab 机制完全隔离。

详细设计见 `docs/superpowers/specs/2026-06-21-account-style-ux-redesign.md`。

## Goals / Non-Goals

**Goals:**
- 将巨型弹窗+Tab 改为独立弹窗+卡片操作按钮，拆分为多个职责单一的组件
- 新建账号使用三步向导引导用户完成完整流程
- 蒸馏弹窗左右分栏，直观展示"参考文章→风格画像"的推导关系
- 蒸馏任务提供实时进度反馈（轮询 + 进度条 + 维度状态 + 错误重试）
- 修复 `word_count` 字段在前后端缺失的问题

**Non-Goals:**
- 任务中心（Task Center）通用设计 — 留作后续独立 feature
- 其他异步操作（文章创作、素材采集）的进度改造
- 蒸馏历史版本管理

## Decisions

### 1. 组件拆分策略

**决策**: 将 `AccountsView.vue` 拆分为 1 个页面组件 + 5 个子组件

**理由**: 当前 618 行单文件无法维护，每个子组件对应一个独立职责。Vue 3 组合式 API 下组件拆分成本低。

**备选**: 保持单文件但提取 composables → 被否决，因为 UI 结构也在膨胀，不是只有逻辑问题。

### 2. 蒸馏进度反馈：轮询 vs SSE

**决策**: 使用 HTTP 轮询（2 秒间隔），不引入 SSE

**理由**:
- 蒸馏耗时 ~30-60 秒，2 秒轮询产生 15-30 次请求，完全可接受
- 无需引入 SSE 基础设施（EventSource、连接管理、重连逻辑）
- 后端只需新增一个 GET 端点，改动最小
- SSE 留作未来任务中心统一改造时再引入

**备选**: SSE 实时推送 → 体验更好但改动更大，当前需求量级不足以支撑引入新协议。

### 3. 蒸馏任务：单次 vs 拆分 LLM 调用

**决策**: 将 1 次 LLM 调用拆分为 7 次独立调用，每维度一次

**理由**:
- 用户选择精确进度反馈，只有拆分才能显示"已完成 4/7 维度"
- 每个维度的 prompt 更聚焦，可能提升蒸馏质量
- 单维度失败可重试单维度（后续优化，当前失败则整体标记 failed）

**代价**: API 调用次数增加 7 倍，但每维度 prompt 更短，总耗时可能增加但总 token 数不一定翻倍。蒸馏是低频操作（每账号几次），成本可接受。

### 4. 进度状态存储：复用 Account model vs 新建任务表

**决策**: 复用 Account model 已有字段（`style_profile_status`, `style_profile_structured`），不新建表

**理由**:
- Account model 已有 `style_profile_status`（String）和 `style_profile_structured`（JSON Text）
- 蒸馏是单任务（一个账号同一时间只有一个蒸馏任务），不需要任务队列表
- 进度信息（`{completed: 4, total: 7, current: "句式特征"}`）存储在 `style_profile_structured` 中或单独字段中即可

**备选**: 新建 `DistillTask` 表 → 更规范但过度设计，当前无多任务并发需求。

### 5. 前端轮询生命周期

**决策**: 轮询绑定到 DistillDialog 组件生命周期

- 点击蒸馏 → 开始轮询（每 2s）
- status === "completed" | "failed" → 停止轮询
- 弹窗关闭（onUnmounted）→ 停止轮询
- 5 分钟超时 → 停止轮询 + 提示超时
- 网络错误 → 重试 3 次后停止

## Risks / Trade-offs

- **[7 次 LLM 调用耗时增加]** → 每次调用仅聚焦单维度，prompt 更短；可在 UI 上展示"预计 30-60 秒"管理预期
- **[轮询增加后端负载]** → 2 秒间隔 + 蒸馏 30-60 秒 = 15-30 次 DB 查询，可忽略不计
- **[页面刷新丢失轮询状态]** → 轮询幂等：重新打开蒸馏弹窗时立即查询 status，running 则恢复轮询
- **[Celery worker 崩溃导致 status 卡在 running]** → 前端 5 分钟超时兜底；后端可后续加心跳检测
- **[`word_count_options` 数据迁移]** → 新增列设默认值 NULL，不影响已有数据；前端做空值兜底
