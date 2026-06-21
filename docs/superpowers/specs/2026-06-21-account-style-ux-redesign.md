# 账号风格功能交互重构 — 设计文档

**日期**: 2026-06-21
**状态**: 设计完成，待实施

---

## 一、问题陈述

当前账号风格功能（`/accounts` 页面）存在以下三个核心问题：

1. **新增/编辑账号交互不友好**：使用单一弹窗 + 4 个 Tab（基本信息、参考文章、风格画像、字数配置），Tab 之间独立操作，用户需频繁切换。
2. **参考文章与风格画像分离**：两者是输入→输出的依赖关系，但放在两个独立 Tab 中，割裂了操作流程。
3. **风格蒸馏无进度反馈**：点击"蒸馏风格"后仅 toast "已提交"，用户无法感知是否在执行、进度如何、是否出错。

### 额外发现的 Bug

4. **`word_count` / `word_count_options` 字段缺失**：前端 `AccountsView.vue` 使用了 `word_count` 和 `word_count_options` 字段，但后端 Account model 和 Pydantic schema 均无此字段。`tasks.py:trigger_generate` 中 `account.word_count` 会在运行时抛出 `AttributeError`。

---

## 二、设计方案

### 2.1 交互模型重构

| 场景 | 当前 | 改为 |
|------|------|------|
| 新建账号 | 弹窗 + 4 Tab | **三步向导**（Stepper） |
| 编辑基本信息 | Tab "基本信息" | **独立弹窗** |
| 风格蒸馏 | Tab "参考文章" + "风格画像" | **独立弹窗**（左右分栏） |
| 字数配置 | Tab "字数配置" | **独立弹窗** |

#### 2.1.1 新建账号 — 三步向导

点击"新增账号"按钮 → 打开向导（el-dialog 内含 el-steps）：

- **Step 1 — 基本信息**：平台（下拉选择）、账号名称（文本输入）。必填校验通过后可进入下一步。
- **Step 2 — 添加参考文章**：文章列表 + 添加按钮。添加文章使用内嵌表单或子弹窗。至少 1 篇文章方可进入下一步。建议 3~5 篇。
- **Step 3 — 确认并蒸馏**：展示已填写的信息摘要（平台、账号名、文章数量）。点击"开始蒸馏"→ 提交创建账号 + 参考文章 + 触发蒸馏 → 关闭向导 → 跳转到账号列表，对应的新账号卡片显示蒸馏进度。

**组件拆分**：当前 `AccountsView.vue`（618 行单文件）拆分为：
- `AccountsView.vue` — 页面主体（卡片列表 + 新增按钮）
- `AccountWizard.vue` — 三步向导组件
- `AccountCard.vue` — 账号卡片组件（含操作按钮）
- `BasicInfoDialog.vue` — 基本信息编辑弹窗
- `DistillDialog.vue` — 风格蒸馏弹窗（左右分栏）
- `WordCountDialog.vue` — 字数配置弹窗

#### 2.1.2 编辑 — 基本信息弹窗

- 字段：平台、账号名称
- 保存后刷新卡片列表

#### 2.1.3 编辑 — 蒸馏弹窗（左右分栏）

- **左侧（~40% 宽度）**：参考文章列表
  - 文章项：标题、字数、代表篇标记
  - 点击文章可编辑/删除（内嵌或子弹窗）
  - "添加文章"按钮
  - 蒸馏进行中时列表置灰不可编辑
- **右侧（~60% 宽度）**：风格画像 + 蒸馏控制
  - **就绪状态**：7 维度网格概览（每维度图标+标签+完成状态）+ "重新蒸馏"按钮
  - **进行中状态**：进度条 + 当前维度文字 + 逐维度完成指示器 + 预计剩余时间
  - **失败状态**：错误信息 + "查看详情"展开原始错误 + "重试蒸馏"按钮

#### 2.1.4 编辑 — 字数配置弹窗

- 动态字数选项列表（添加/删除）
- 默认字数下拉选择
- 保存调用 `PUT /accounts/{id}`

#### 2.1.5 账号卡片交互

卡片展示：头像（首字）、账号名、平台、风格状态 Badge（画像就绪/待蒸馏）、更新时间。

操作按钮（卡片底部）：
- **基本信息** → 打开基本信息弹窗
- **风格蒸馏** → 打开蒸馏弹窗
- **字数配置** → 打开字数配置弹窗

删除操作放在卡片右上角更多菜单（`el-dropdown`）中。

**蒸馏状态指示**：卡片上的状态 Badge 实时反映 `style_profile_status`：
- `idle` / `none` → "待蒸馏"（橙色）
- `running` → "蒸馏中..."（蓝色 + loading 动画）
- `ready` → "画像就绪 v{n}"（绿色）
- `failed` → "蒸馏失败"（红色，可点击重试）

---

### 2.2 蒸馏进度反馈机制

#### 2.2.1 后端改动

**新增 `GET /accounts/{id}/distill/status` 接口**

返回格式：

```json
// 空闲
{ "status": "idle" }

// 进行中
{
  "status": "running",
  "task_id": "celery-uuid",
  "started_at": "2026-06-21T10:30:00",
  "progress": { "completed": 4, "total": 7, "current_dimension": "句式特征" }
}

// 已完成
{
  "status": "completed",
  "completed_at": "2026-06-21T10:30:45",
  "style_profile_version": 3
}

// 失败
{
  "status": "failed",
  "error": "LLM 返回格式异常: JSONDecodeError...",
  "failed_at": "2026-06-21T10:31:00"
}
```

**Celery 任务拆分**：将 `trigger_distill` 的一次 LLM 调用拆分为 7 次独立调用，每次聚焦一个维度：

1. `thinking_pattern` — 思维模式
2. `structure_pattern` — 结构模式
3. `sentence_pattern` — 句式特征
4. `vocabulary_pattern` — 词汇偏好
5. `evidence_type` — 论据类型
6. `taboos` — 写作禁忌
7. `blank_leaving` — 留白习惯

流程：
```
开始 → 设 status="running"
  → 调用 LLM（维度 1/7）→ 写入 style_profile_structured.{dim1} → 更新进度
  → 调用 LLM（维度 2/7）→ 写入 style_profile_structured.{dim2} → 更新进度
  → ...
  → 调用 LLM（维度 7/7）→ 写入 style_profile_structured.{dim7} → 更新进度
  → 设 status="ready", version++, updated_at=now()
```

任一次 LLM 调用失败 → 设 status="failed"，记录错误信息。

**利用现有字段**：
- `style_profile_status`（已有，String(20)）：值改为 `idle / running / ready / failed`
- `style_profile_structured`（已有，JSON Text）：逐维度写入
- `style_profile_version`（已有，Integer）：成功后递增
- `style_profile_updated_at`（已有，DateTime）：成功后更新

**无需新建数据表**，无需新增 Celery task 表。进度信息直接从 Account 记录读取。

**修复 `word_count` 字段**：
- Account model 新增 `word_count_options`（JSON Text）和 `word_count`（Integer, nullable）
- AccountUpdate schema 新增对应字段
- AccountResponse schema 新增对应字段
- 前端 TypeScript `Account` 接口补充 `word_count_options` 和 `word_count`

#### 2.2.2 前端轮询

- 点击蒸馏后，每 **2 秒** 轮询 `GET /accounts/{id}/distill/status`
- 根据 `status` 更新 UI（进度条 / 完成展示 / 错误提示）
- `status === "completed"` 或 `"failed"` 时停止轮询
- 弹窗关闭时停止轮询
- **超时保护**：5 分钟后未完成则提示"蒸馏超时，请稍后重试"，停止轮询
- 轮询错误（网络异常等）重试 3 次后提示"无法获取蒸馏状态"

---

## 三、文件变更范围

### 前端

| 文件 | 操作 |
|------|------|
| `src/views/AccountsView.vue` | **重写** — 移除巨型弹窗，改为卡片列表 + 独立弹窗触发 |
| `src/components/accounts/AccountCard.vue` | **新增** — 卡片组件（头像、信息、状态 Badge、操作按钮） |
| `src/components/accounts/AccountWizard.vue` | **新增** — 三步新建向导 |
| `src/components/accounts/BasicInfoDialog.vue` | **新增** — 基本信息编辑弹窗 |
| `src/components/accounts/DistillDialog.vue` | **新增** — 蒸馏弹窗（左右分栏 + 进度） |
| `src/components/accounts/WordCountDialog.vue` | **新增** — 字数配置弹窗 |
| `src/components/accounts/ReferenceArticleForm.vue` | **新增** — 参考文章表单（在 Wizard Step2 和 DistillDialog 中复用） |
| `src/api/modules/accounts.ts` | **修改** — 补充 `word_count` 字段、新增 `getDistillStatus()` |
| `src/api/types.ts` | **修改** — `Account` 接口补充字段 |

### 后端

| 文件 | 操作 |
|------|------|
| `app/api/distill.py` | **修改** — 新增 `GET /accounts/{id}/distill/status` 路由 |
| `app/tasks.py` | **修改** — `trigger_distill` 拆分为 7 次独立 LLM 调用 + 进度更新 |
| `app/models.py` | **修改** — Account 新增 `word_count_options`, `word_count`；`style_profile_status` 注释更新 |
| `app/schemas.py` | **修改** — AccountUpdate/AccountResponse 补充 `word_count` 字段 |

### 数据库迁移

- Account 表新增 `word_count_options`（JSON Text）、`word_count`（Integer, nullable）
- 已有字段 `style_profile_status` 值域变更（已有数据兼容：`none→idle`, `ready→ready`）

---

## 四、状态覆盖

### 蒸馏弹窗状态

| 状态 | 条件 | 左侧（文章） | 右侧（画像） |
|------|------|-------------|-------------|
| **空态** | 无参考文章 | 空列表 + "添加第一篇文章"引导 | "请先添加参考文章" |
| **就绪** | 有文章，未蒸馏或已蒸馏 | 正常操作 | 画像展示（如有）+ 蒸馏按钮 |
| **蒸馏中** | status=running | 置灰不可编辑 | 进度条 + 维度状态 |
| **完成** | status=ready | 恢复正常 | 画像展示 + 重新蒸馏按钮 |
| **失败** | status=failed | 恢复正常 | 错误信息 + 重试按钮 |
| **轮询超时** | 5分钟未完成 | 恢复正常 | 超时提示 + 重试按钮 |

### 卡片状态 Badge

| status | Badge 文案 | 颜色 |
|--------|-----------|------|
| `idle` / `none` / null | 待蒸馏 | 橙色 |
| `running` | 蒸馏中... | 蓝色 + loading |
| `ready` | 画像就绪 v{n} | 绿色 |
| `failed` | 蒸馏失败 | 红色 |

### 向导 Step 流转

```
Step 1 (基本信息) ──[校验通过]──→ Step 2 (参考文章)
Step 2 ──[至少1篇文章]──→ Step 3 (确认并蒸馏)
Step 3 ──[点击蒸馏]──→ 提交 + 关闭 + 卡片显示蒸馏进度
```

---

## 五、非目标（不在本次范围）

- 任务中心（Task Center）通用设计 — 留作后续独立 feature
- 其他异步操作的进度改造（文章创作、素材采集）
- 蒸馏历史记录/版本回溯
- 批量蒸馏
