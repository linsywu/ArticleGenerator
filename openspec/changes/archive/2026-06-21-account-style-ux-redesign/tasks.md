## 1. Backend — 数据模型修复

- [ ] 1.1 Account model 新增 `word_count_options` (JSON Text) 和 `word_count` (Integer) 列
- [ ] 1.2 生成数据库迁移（手动 SQL 或 Alembic），确保已有数据不受影响
- [ ] 1.3 AccountUpdate / AccountResponse Pydantic schema 补充 `word_count_options` 和 `word_count` 字段
- [ ] 1.4 更新 `style_profile_status` 注释，值域改为 `idle / running / ready / failed`

## 2. Backend — 蒸馏状态接口

- [ ] 2.1 新增 `GET /accounts/{account_id}/distill/status` 路由
- [ ] 2.2 查询 Account 的 `style_profile_status`, `style_profile_structured`, `style_profile_version`
- [ ] 2.3 running 状态时返回 progress 元数据（completed, total, current_dimension）
- [ ] 2.4 编写接口测试：idle / running / completed / failed 四种状态返回正确

## 3. Backend — 蒸馏任务拆分

- [ ] 3.1 拆分 `trigger_distill` 为 7 次独立 LLM 调用，每次聚焦一个维度
- [ ] 3.2 每维度完成后更新 `style_profile_structured` 对应字段 + progress metadata
- [ ] 3.3 任务开始时设 `style_profile_status = "running"`
- [ ] 3.4 全部完成时设 `style_profile_status = "ready"`，递增 `version`，更新 `updated_at`
- [ ] 3.5 任一维度失败时设 `style_profile_status = "failed"` 并记录错误信息
- [ ] 3.6 编写测试：模拟 LLM 响应，验证进度更新和最终状态

## 4. Frontend — API 层更新

- [ ] 4.1 `src/api/types.ts` 中 Account 接口补充 `word_count_options`, `word_count`, `style_profile_status` 字段
- [ ] 4.2 `src/api/modules/accounts.ts` 或 `client.ts` 新增 `getDistillStatus(accountId)` 方法
- [ ] 4.3 account CRUD 方法签名补充 word_count 相关字段

## 5. Frontend — 新组件实现

- [ ] 5.1 创建 `src/components/accounts/AccountCard.vue` — 卡片组件（头像、信息、状态 Badge、三个操作按钮、删除菜单）
- [ ] 5.2 创建 `src/components/accounts/ReferenceArticleForm.vue` — 参考文章表单（在 Wizard Step2 和 DistillDialog 中复用）
- [ ] 5.3 创建 `src/components/accounts/BasicInfoDialog.vue` — 基本信息编辑弹窗
- [ ] 5.4 创建 `src/components/accounts/WordCountDialog.vue` — 字数配置弹窗
- [ ] 5.5 创建 `src/components/accounts/AccountWizard.vue` — 三步向导（基本信息 → 参考文章 → 确认并蒸馏）
- [ ] 5.6 创建 `src/components/accounts/DistillDialog.vue` — 蒸馏弹窗（左右分栏 + 轮询进度 + 错误重试）

## 6. Frontend — 页面重构

- [ ] 6.1 重写 `src/views/AccountsView.vue` — 卡片网格布局，移除巨型弹窗和 Tab
- [ ] 6.2 集成所有新组件，管理弹窗可见性和数据流
- [ ] 6.3 蒸馏状态 Badge 在卡片上实时更新（从轮询或列表刷新获取最新 status）

## 7. 测试

- [ ] 7.1 后端单元测试：`test_distill_status_endpoint.py` — 验证 status 接口四种状态返回
- [ ] 7.2 后端单元测试：`test_distill_task_progress.py` — 验证 trigger_distill 拆分调用和进度更新
- [ ] 7.3 后端单元测试：`test_account_word_count.py` — 验证 word_count 字段 CRUD
- [ ] 7.4 前端 E2E：向导创建账号流程 → 蒸馏 → 画像展示
- [ ] 7.5 前端 E2E：蒸馏进度轮询（mock 后端 status 接口，验证 UI 状态变化）
- [ ] 7.6 前端 E2E：蒸馏失败 + 重试流程
- [ ] 7.7 前端 E2E：蒸馏超时处理
- [ ] 7.8 手动验证：启动 dev server 实际访问页面，确认所有流程正常

## 8. 清理

- [ ] 8.1 移除旧的 Tab/Dialog 相关代码（如已无引用）
- [ ] 8.2 确认所有现有测试仍通过
- [ ] 8.3 提交代码
