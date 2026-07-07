# 风格蒸馏特征清单持久化 设计

**日期**: 2026-07-07
**状态**: 已确认，待实现
**关联**: 增强 [`2026-07-06-distill-quality-redesign`](./2026-07-06-distill-quality-redesign.md)。两阶段蒸馏已上线，但 Stage 1 的特征清单（带原文引证的证据）未持久化，蒸馏结束即丢失。本设计补齐持久化 + 展示。

## 背景与问题

两阶段蒸馏产出两个层次的内容：

| 产物 | Stage | 内容 | 服务对象 |
|------|-------|------|---------|
| **特征清单 features** | Stage 1 | 作者类型 + 5-8 条带「原文引证」的证据 | 人（审计/透明度） |
| **写作风格指南 guide** | Stage 2 | 开头/结尾/标志词/禁忌等可执行指令 | LLM（生成）+ 人（主参考） |

当前只有 guide 存入 `account.style_profile`，features 拿到后仅作为 Stage 2 输入用完即丢。用户在弹窗里看不到证据清单，无法审计"蒸馏是否抓对了特征"。

## 目标

持久化 features 并在弹窗展示，**同时不污染下游生成注入**。

## 核心决策

**features 与 guide 服务不同对象，必须分离存储：**

- guide 是给生成 LLM 的合成指令 → 注入 `{{style_profile}}`
- features 是给人的分析证据 → **不注入任何生成任务**（Stage 2 已把证据合成进指令，再注入原始证据是噪声）

合并二者到 `style_profile` 会污染下游 4 个生成模板（direction/outline/title/generate）的注入，部分抵消 Stage 2 的合成价值。

## 方案：新字段 `style_features`（折叠展示）

### 数据模型
- 新列 `Account.style_features = Column(Text)` — 存 Stage 1 输出（证据清单）
- 迁移 `021_add_style_features.sql`：`ALTER TABLE accounts ADD COLUMN style_features TEXT;`
- `schemas.py`：`AccountResponse.style_features: Optional[str] = None`

### trigger_distill 落库
Stage 1 成功后**立即**存 `style_features`（Stage 2 失败也能保留证据供调试），Stage 2 完成后存 `style_profile`：

```python
# Stage 1 成功后（标记 synthesizing 时）
account.style_features = features   # NEW：保留证据

# Stage 2 完成后
account.style_profile = guide
```

### 下游注入——零改动（关键）
`{{style_profile}}` 仍是 guide only。`style_features` **不注入任何生成任务**——只服务人（展示/审计）。direction/outline/title/generate 四个模板完全不动，Gateway 仍只注入 `account.style_profile`。

### 前端 DistillDialog（折叠面板布局）
- `types.ts`：`Account.style_features?: string`
- 弹窗右侧"风格画像"区：
  - 主区 `.guide-text` 展示 `account.style_profile`（指南，不变）
  - 下方 `<el-collapse>` 折叠"▸ 查看证据清单（作者类型 + 引证特征）"，展开显示 `account.style_features`
  - **`style_features` 为空时（老账号 NULL）隐藏折叠区**，避免空块

## 测试计划

- `test_distill_task.py`：新增断言 `style_features` 蒸馏后被填充
- 浏览器验证（前端验证铁律）：陆拾一弹窗能看到折叠的证据清单，展开后显示带「引证」的特征；老账号（features 为空）不显示折叠区

## 边界情况

- 老账号 `style_features = NULL` → 折叠区隐藏
- 重新蒸馏 → 两个字段都覆盖
- Stage 2 失败但 Stage 1 成功 → `style_features` 已存、`status=failed`（可接受，便于调试）

## 改动文件清单

| 文件 | 改动 |
|------|------|
| `ArticleGeneratorService/app/models.py` | 新增 `style_features` 列 |
| `ArticleGeneratorService/app/schemas.py` | 新增 `style_features` 字段 |
| `ArticleGeneratorService/app/tasks.py` | `trigger_distill` Stage 1 后存 `style_features` |
| `ArticleGeneratorService/tests/test_distill_task.py` | 新增 `style_features` 断言 |
| `ArticleGeneratorDatabase/migrations/021_add_style_features.sql` | ADD COLUMN |
| `ArticleGeneratorAdm/src/api/types.ts` | `Account.style_features?: string` |
| `ArticleGeneratorAdm/src/components/accounts/DistillDialog.vue` | 折叠面板展示证据清单 |
