## Why

账号风格管理页面当前使用巨型弹窗+4Tab交互，参考文章与风格画像分离，蒸馏过程无进度反馈——用户操作割裂、无法感知异步任务状态，严重影响可用性。

## What Changes

- **BREAKING**: 账号卡片交互从"点击打开4Tab弹窗"改为"卡片上独立操作按钮"（基本信息/风格蒸馏/字数配置三个独立弹窗）
- 新建账号从 Tab 式改为三步向导（基本信息 → 参考文章 → 确认并蒸馏）
- 参考文章和风格画像合并到同一个蒸馏弹窗，左右分栏展示输入→输出关系
- 风格蒸馏新增实时进度反馈：前端轮询 + 进度条 + 维度逐个完成指示器 + 错误展示 + 重试
- 后端蒸馏任务从单次 LLM 调用拆分为 7 次独立调用（每维度一次），提供精确进度
- 新增 `GET /accounts/{id}/distill/status` 轮询接口
- 修复 `word_count` / `word_count_options` 字段在 Model、Schema、前端类型中缺失的问题

## Capabilities

### New Capabilities
- `account-wizard`: 三步向导创建账号（基本信息→参考文章→确认并蒸馏）
- `distill-progress`: 风格蒸馏进度实时反馈（轮询、进度条、维度状态、错误重试）

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- **前端**: `AccountsView.vue` 重写；新增 `AccountCard`, `AccountWizard`, `BasicInfoDialog`, `DistillDialog`, `ReferenceArticleForm`, `WordCountDialog` 组件；API 模块和类型定义更新
- **后端**: `app/api/distill.py` 新增 status 路由；`app/tasks.py` 蒸馏任务重写；`app/models.py` 和 `app/schemas.py` 补充 word_count 字段
- **数据库**: Account 表新增 `word_count_options` (JSON Text) 和 `word_count` (Integer) 列
- **无破坏性 API 变更**: 现有 API 端点签名不变，仅新增 status 端点
