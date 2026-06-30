# 文章创作全流程测试计划

## 上下文

需要对文章创作完整流程（选择账号 → 输入想法 → 创作写作方向 → 生成大纲 → 生成标题 → 生成全文 → 文章评审 → 微调 → 文章发布）编写全面覆盖的单元测试和 E2E 测试，使用 Playwright 等工具进行真实测试，修复所有发现的 bug，迭代直至全流程通过。

### 当前测试基础设施
- **后端**: pytest + FastAPI TestClient + SQLite 临时数据库，conftest.py 提供 `client`/`auth_client`/`db_session` fixtures，autouse `_clean_db` 保障测试隔离
- **Celery 任务测试**: 使用 `unittest.mock.patch("app.tasks.httpx.Client")` mock HTTP 调用，`_mock_chat_response()` 辅助函数
- **前端**: Playwright 已配置 (`playwright.config.ts`)，已有 `e2e/auth.setup.ts` 和 `e2e/materials-direction.spec.ts`
- **Vitest**: 已配置 `jsdom` 环境，但 Vue SFC 动态 import 不兼容

### 已知陷阱（来自 memory）
- LLM 返回空 → 先 curl gateway 确认根因，不要盲目改代码
- Celery 任务缺少 `user_prompt` 是历史重复问题
- 前端验证必须启动 dev server 实际访问页面
- Outline 返回 `string[]`，前端期望 `{order, point}[]`

---

## 测试策略

### Phase 1: 后端单元测试（pytest，mock LLM）

覆盖 9 个步骤的 API 端点和 Celery 任务逻辑，不依赖真实 LLM 服务。

### Phase 2: 前端 E2E 测试（Playwright，真实浏览器）

使用预置 token 绕过登录，覆盖完整 UI 交互流程。

### Phase 3: 运行测试 → 记录 Bug → 修复 → 重测

迭代直至全部通过。每次迭代：跑全部测试 → 记录失败项 → 分析根因 → 修复业务代码 → 重新验证。

---

## Phase 1: 后端测试用例设计

### 文件: `tests/test_workflow_direction.py` — 写作方向生成

| # | 测试名 | 覆盖内容 |
|---|--------|---------|
| 1 | `test_post_directions_returns_task_id` | API 返回 task_id 和 pending 状态 |
| 2 | `test_post_directions_empty_idea_rejected` | 空白 idea 返回 400 |
| 3 | `test_post_directions_account_id_zero_accepted` | 素材中心路径 account_id=0 正常 |
| 4 | `test_direction_task_json_array_format` | LLM 返回 JSON 数组 `[{id, title}]` |
| 5 | `test_direction_task_json_object_format` | LLM 返回 `{directions: [...]}` |
| 6 | `test_direction_task_markdown_code_block` | LLM 返回 ` ```json ... ``` ` 代码块 |
| 7 | `test_direction_task_numbered_list_fallback` | 编号列表回退解析 `1. title` |
| 8 | `test_direction_task_chinese_numbered_fallback` | 中文格式 `方向一：title` |
| 9 | `test_direction_task_letter_prefix_fallback` | 字母前缀 `A. title` / `A) title` |
| 10 | `test_direction_task_empty_content_raises` | LLM 返回空内容抛 ValueError |
| 11 | `test_direction_task_unparseable_content_raises` | 无法解析的内容抛 ValueError |
| 12 | `test_direction_task_candidate_fallback` | ≥3 个候选行时兜底解析（最终 fallback） |
| 13 | `test_task_result_endpoint_success` | GET /task/{id}/result 返回正确结构 |
| 14 | `test_task_result_endpoint_failed` | 失败任务返回 error_message |

### 文件: `tests/test_workflow_outline.py` — 大纲生成

| # | 测试名 | 覆盖内容 |
|---|--------|---------|
| 1 | `test_post_outline_returns_task_id` | API 返回 task_id |
| 2 | `test_post_outline_account_not_found` | 账号不存在返回 404 |
| 3 | `test_post_outline_empty_idea_rejected` | 空白 idea 返回 400 |
| 4 | `test_post_outline_empty_direction_rejected` | 空白 direction 返回 400 |
| 5 | `test_outline_task_json_array` | LLM 返回 JSON 字符串数组 |
| 6 | `test_outline_task_json_object` | LLM 返回 `{outline: [...]}` |
| 7 | `test_outline_task_markdown_code_block` | Markdown 代码块 |
| 8 | `test_outline_task_user_prompt_included` | 验证 user_prompt 被传入 LLM 请求 |
| 9 | `test_outline_task_empty_content_raises` | 空内容抛异常 |

### 文件: `tests/test_workflow_title.py` — 标题生成

| # | 测试名 | 覆盖内容 |
|---|--------|---------|
| 1 | `test_post_titles_returns_task_id` | API 返回 task_id |
| 2 | `test_post_titles_account_not_found` | 404 处理 |
| 3 | `test_post_titles_empty_idea_rejected` | 空 idea 400 |
| 4 | `test_title_task_json_array` | LLM 返回字符串数组 |
| 5 | `test_title_task_markdown_code_block` | Markdown 代码块解析 |
| 6 | `test_title_task_empty_fallback_to_idea` | 无结果时回退到 idea 作为标题 |
| 7 | `test_title_task_user_prompt_included` | 验证 user_prompt 被传入 |

### 文件: `tests/test_workflow_generate.py` — 全文生成

| # | 测试名 | 覆盖内容 |
|---|--------|---------|
| 1 | `test_trigger_with_custom_topic` | 自定义主题触发（无热点 ID） |
| 2 | `test_trigger_with_outline` | 带大纲触发生成 |
| 3 | `test_trigger_with_word_count` | 字数参数传递 |
| 4 | `test_generate_task_creates_article` | 验证 Article 记录写入 DB |
| 5 | `test_generate_task_updates_generation_task` | 验证 GenerationTask status → success |
| 6 | `test_generate_task_resolve_title` | 标题解析逻辑（传入标题优先、H1/H2/首行回退） |
| 7 | `test_generate_task_empty_llm_response_raises` | LLM 返回空抛异常 |
| 8 | `test_generate_task_cancelled_skips` | 已取消任务直接退出 |
| 9 | `test_generate_task_style_instructions_in_prompt` | 结构化画像注入到 prompt |
| 10 | `test_task_status_endpoint` | GET /generate/task/{id} 返回正确状态 |
| 11 | `test_generate_triggers_humanize_chain` | 验证链式调用 humanize |

### 文件: `tests/test_workflow_review.py` — 文章评审

| # | 测试名 | 覆盖内容 |
|---|--------|---------|
| 1 | `test_article_status_approve` | pending_review → approved |
| 2 | `test_article_status_reject` | pending_review → rejected |
| 3 | `test_article_status_invalid_transition` | approved → rejected 应 400 |
| 4 | `test_article_status_invalid_value` | 非法状态值 400 |
| 5 | `test_article_status_article_not_found` | 不存在的文章 404 |
| 6 | `test_quality_review_parse_score_total` | `_parse_score` 解析 "总分：85" |
| 7 | `test_quality_review_parse_score_overall` | 解析 "综合评分：70" |
| 8 | `test_quality_review_parse_score_last_number` | 兜底取最后一个合法数字 |
| 9 | `test_compliance_review_safe_detection` | "safe" 关键词 → 100 分 |

### 文件: `tests/test_workflow_refine.py` — 微调

| # | 测试名 | 覆盖内容 |
|---|--------|---------|
| 1 | `test_refine_article_not_found` | 文章不存在 404 |
| 2 | `test_refine_creates_refine_task` | 创建 RefineTask 记录 |
| 3 | `test_refine_updates_article_content` | 验证文章内容更新 |
| 4 | `test_refine_resets_status_to_pending_review` | 微调后状态回到 pending_review |
| 5 | `test_refine_records_history` | refine_history JSON 追加记录 |
| 6 | `test_refine_empty_llm_response_raises` | LLM 返回空 |
| 7 | `test_refine_task_status_endpoint` | GET /generate/refine-task/{id} |

### 文件: `tests/test_workflow_publish.py` — 文章发布

| # | 测试名 | 覆盖内容 |
|---|--------|---------|
| 1 | `test_article_status_publish` | approved → published |
| 2 | `test_article_status_publish_sets_timestamp` | published_at 被设置 |
| 3 | `test_article_status_publish_from_pending_review_rejected` | pending_review → published 应 400 |
| 4 | `test_list_articles_by_status` | 按 status=approved 筛选文章 |
| 5 | `test_update_article_content` | PUT /articles/{id} 更新 content |
| 6 | `test_update_article_not_found` | 404 处理 |

### 文件: `tests/test_workflow_e2e_full.py` — 全流程集成测试

| # | 测试名 | 覆盖内容 |
|---|--------|---------|
| 1 | `test_full_creation_flow_mocked` | Mock LLM，串联 direction→outline→title→generate→review→refine→publish |
| 2 | `test_createview_scenario_validation` | 各步骤输入验证（空值、边界） |

---

## Phase 2: 前端 E2E 测试用例设计

### 扩展现有 `e2e/materials-direction.spec.ts` → 重命名为 `e2e/full-workflow.spec.ts`

**前置条件**：
- 后端服务运行在 :8000
- 数据库有至少 1 个 style_profile_status=ready 的账号
- 场景配置中 direction/outline/title/generate 的 model 设为可用模型
- 使用预置 JWT token 绕过登录（已有模式）

### 测试用例

| # | 测试名 | 覆盖步骤 | 验证点 |
|---|--------|---------|--------|
| 1 | `createView loads with steps and accounts` | 访问 /create | 6 步骤可见、账号列表加载、无 JS 错误 |
| 2 | `step1 select account and proceed` | 选账号 → 下一步 | currentStep 变为 1、显示账号名 |
| 3 | `step2 input idea and generate directions` | 输入想法 → 生成方向 | 轮询完成后显示方向卡片、无控制台错误 |
| 4 | `step3 select direction and generate outline` | 选方向 → 生成大纲 | 大纲列表显示、每项有 order+point |
| 5 | `step4 edit outline and generate titles` | 编辑大纲要点 → 生成标题 | 标题候选列表显示 |
| 6 | `step5 select title and proceed` | 选标题 → 编辑 → 确认 | 进入步骤 6 |
| 7 | `step6 generate full article` | 触发生成 → 等待完成 | 文章内容显示、生成成功消息 |
| 8 | `review view loads articles` | 访问 /review | 表格有数据、质量/合规分数显示 |
| 9 | `review approve article` | 点击通过 | 文章从列表移除（状态变更）、成功消息 |
| 10 | `review reject article` | 点击拒绝 | 成功消息 |
| 11 | `review refine article` | 打开微调 → 输入关键词 → 确认 | 微调任务提交成功 |
| 12 | `publish view loads and publish` | 访问 /publish → 标记已发布 | 文章从列表移除、成功消息 |
| 13 | `materials to create flow` | 访问 /create?idea=xxx&account_id=N | idea 预填、自动跳到 step 1 |
| 14 | `fullWorkflow no console errors` | 贯穿全部步骤 | 每个页面 0 JS 错误 |

### 烟雾测试（无需真实 LLM）

```bash
# 1. 路由可达性检查（17 个路由全部 200）
# 2. 前端 build 无类型错误
# 3. 后端 health check
# 4. 登录 API 正常
```

---

## Phase 3: 执行与修复循环

### 执行顺序

```
1. 启动后端服务 (uvicorn :8000)
2. 启动 Redis + Celery Worker（如需要真实 LLM）
3. 运行后端单元测试: cd ArticleGeneratorService && pytest tests/test_workflow_*.py -v
4. 记录失败项 → 分析根因 → 修复 → 重跑
5. 启动前端 dev server: cd ArticleGeneratorAdm && npm run dev
6. 运行 Playwright E2E: cd ArticleGeneratorAdm && npx playwright test
7. 记录失败项 → 分析根因 → 修复 → 重跑
8. 迭代直到全部通过
```

### Bug 记录模板

```
| # | 测试名 | 错误信息 | 根因 | 修复方案 | 状态 |
```

### 修复原则
- **后端测试 mock LLM**：不需要真实 LLM 即可通过
- **前端测试需要真实后端**：确保 LLM 场景配置正确
- **禁止修测试掩盖 bug**：只修复业务代码
- **每个修复后重跑全部相关测试**：防止回归

---

## 关键文件清单

### 新增测试文件（后端）
- `ArticleGeneratorService/tests/test_workflow_direction.py`
- `ArticleGeneratorService/tests/test_workflow_outline.py`
- `ArticleGeneratorService/tests/test_workflow_title.py`
- `ArticleGeneratorService/tests/test_workflow_generate.py`
- `ArticleGeneratorService/tests/test_workflow_review.py`
- `ArticleGeneratorService/tests/test_workflow_refine.py`
- `ArticleGeneratorService/tests/test_workflow_publish.py`
- `ArticleGeneratorService/tests/test_workflow_e2e_full.py`

### 新增测试文件（前端）
- `ArticleGeneratorAdm/e2e/full-workflow.spec.ts`

### 可能需要修复的业务代码
- `ArticleGeneratorService/app/tasks.py` — Celery 任务
- `ArticleGeneratorService/app/api/generate.py` — API 端点
- `ArticleGeneratorService/app/api/articles.py` — 文章 API
- `ArticleGeneratorService/app/services/article_service.py` — 状态机
- `ArticleGeneratorAdm/src/views/CreateView.vue` — 创作页面
- `ArticleGeneratorAdm/src/views/ReviewView.vue` — 评审页面
- `ArticleGeneratorAdm/src/views/PublishView.vue` — 发布页面

---

## 验证方式

1. **后端**: `cd ArticleGeneratorService && pytest tests/test_workflow_*.py -v --tb=short`，全部 PASS
2. **前端**: `cd ArticleGeneratorAdm && npx playwright test --reporter=line`，全部 PASS
3. **浏览器手动验证**: 启动 dev server，走通完整创作流程，控制台 0 错误
4. **构建验证**: `npm run build` 无错误
