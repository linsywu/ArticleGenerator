## 1. Backend: Unit Tests

- [x] 1.1 `test_workflow_direction.py` — 17 tests：API + Celery task + 7 种解析格式 + AsyncResult 端点
- [x] 1.2 `test_workflow_outline.py` — 9 tests：API + Celery task + user_prompt 验证
- [x] 1.3 `test_workflow_title.py` — 8 tests：API + Celery task + 回退逻辑 + 非字符串过滤
- [x] 1.4 `test_workflow_generate.py` — 14 tests：API + resolve_article_title 纯函数 + DB 验证
- [x] 1.5 `test_workflow_review.py` — 18 tests：状态机 + _parse_score + API 端点
- [x] 1.6 `test_workflow_refine.py` — 9 tests：API + DB 验证 + 失败状态记录
- [x] 1.7 `test_workflow_publish.py` — 8 tests：API + 状态转换 + 文章更新
- [x] 1.8 `test_workflow_e2e_full.py` — 10 tests：全流程集成 + 输入验证 + 边界场景

## 2. Frontend: E2E Tests

- [x] 2.1 `e2e/full-workflow.spec.ts` — 11 tests：页面加载、步骤导航、方向/大纲/标题生成、评审/发布页面
- [x] 2.2 `e2e/materials-direction.spec.ts` — 4 tests：更新适配新的 MaterialsDirectionDialog CSS 类名

## 3. Bug Fix

- [x] 3.1 `CreateView.vue` line 161：修复"确认标题 · 生成全文"按钮 — `@click="startGenerate()"` 替代 `@click="currentStep = 5"`

## 4. Verification

- [x] 4.1 后端全部测试通过：93/93 passed
- [x] 4.2 前端 E2E 全部通过：15/15 passed
- [x] 4.3 前端构建通过：无错误
- [x] 4.4 浏览器手动验证：/create 页面控制台无 JS 错误
- [x] 4.5 真实 LLM 调用验证：direction generation 返回 5 个有效方向
