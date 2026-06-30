## Why

文章创作全流程（选择账号 → 输入想法 → 创作方向 → 大纲 → 标题 → 全文 → 评审 → 微调 → 发布）缺乏系统化的自动化测试覆盖。前端 E2E 测试仅覆盖素材中心方向对话框，后端缺少对 direction/outline/title/refine 等步骤的完整 Celery 任务测试。缺乏测试导致历史重复 Bug 未被及时发现（如 user_prompt 缺失、outline 数据格式不匹配等）。

## What Changes

- 新增 8 个后端测试文件（93 个测试用例），覆盖 direction/outline/title/generate/review/refine/publish 全流程
- 新增前端 Playwright E2E 测试 `full-workflow.spec.ts`（11 个测试用例），覆盖完整 UI 交互流程
- 更新 `materials-direction.spec.ts` 适配重写后的 MaterialsDirectionDialog 新 CSS 类名
- 修复 Critical Bug：`CreateView.vue` 中"确认标题 · 生成全文"按钮未调用 `startGenerate()`，导致用户到达步骤 6 后无法触发生成

## Capabilities

### New Capabilities
- `workflow-test-direction`: 写作方向 API + Celery 任务 + 解析器全覆盖测试
- `workflow-test-outline`: 大纲 API + Celery 任务 + user_prompt 验证测试
- `workflow-test-title`: 标题 API + Celery 任务 + 回退逻辑测试
- `workflow-test-generate`: 全文生成 API + resolve_article_title 纯函数 + DB 验证测试
- `workflow-test-review`: 评审状态机 + _parse_score + API 端点测试
- `workflow-test-refine`: 微调 API + DB 记录验证 + 状态重置测试
- `workflow-test-publish`: 发布 API + 状态转换 + 文章更新测试
- `workflow-test-e2e-full`: 全流程集成测试（Mock LLM 串联 9 步骤）
- `e2e-full-workflow`: Playwright 浏览器 E2E（真实 LLM 调用，控制台错误检测）

### Modified Capabilities
- `create-view-generate`: 修复步骤 6 全文生成触发（按钮绑定 `startGenerate()`）

## Impact

### 新增文件
- `ArticleGeneratorService/tests/test_workflow_direction.py` — 17 tests
- `ArticleGeneratorService/tests/test_workflow_outline.py` — 9 tests
- `ArticleGeneratorService/tests/test_workflow_title.py` — 8 tests
- `ArticleGeneratorService/tests/test_workflow_generate.py` — 14 tests
- `ArticleGeneratorService/tests/test_workflow_review.py` — 18 tests
- `ArticleGeneratorService/tests/test_workflow_refine.py` — 9 tests
- `ArticleGeneratorService/tests/test_workflow_publish.py` — 8 tests
- `ArticleGeneratorService/tests/test_workflow_e2e_full.py` — 10 tests
- `ArticleGeneratorAdm/e2e/full-workflow.spec.ts` — 11 tests

### 修改文件
- `ArticleGeneratorAdm/src/views/CreateView.vue` — line 161: `@click="currentStep = 5"` → `@click="startGenerate()"`
- `ArticleGeneratorAdm/e2e/materials-direction.spec.ts` — 适配新 UI CSS 类名

### 验证结果
- 后端：93/93 passed
- 前端 E2E：15/15 passed（11 new + 4 existing）
- 前端构建：无错误
