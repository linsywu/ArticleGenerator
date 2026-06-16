# Implementation Tasks

## 1. P0 — 安全与正确性

- [ ] 1.1 T01 — JWT 鉴权基础框架：新增 User 模型 + app/auth.py + app/deps.py + POST /api/auth/login + 前端 LoginView + router 守卫
- [ ] 1.2 T02 — Provider api_key 脱敏：响应掩码 + 写入留空不修改 + LLMService 取完整 key
- [ ] 1.3 T03 — 统一数据库 Engine：删除 tasks.py 独立 create_engine + SQLite 绝对路径
- [ ] 1.4 T04 — 修复 CreateView 步骤 6 死代码：删除模板 + submitForReview + 5 步指示器
- [ ] 1.5 T05 — 清理孤儿页面：删除 GenerateView.vue + DistillView.vue + 确认无残留引用
- [ ] 1.6 T06 — 修复 CORS 配置：具体 origin 列表 + 解除 ["*"] + credentials=True 组合

## 2. P1 — 架构与性能

- [ ] 2.1 T07 — 移除 Router 内 Celery 同步阻塞：三处 task.get(timeout=120) 改为 delay()
- [ ] 2.2 T08 — 抽取 Service 层：新建 services/generate_service.py + article_service.py + 瘦身 Router
- [ ] 2.3 T09 — 拆分 Celery tasks：celery_app.py + tasks/ 包 + utils/json_parse.py
- [ ] 2.4 T10 — 前端 API 层重构：client.ts 瘦身 + 5 域文件 + api/index.ts
- [ ] 2.5 T11 — 抽取核心前端组件与 hooks：ArticleEditorDialog + PageHeader + usePaginatedList + useActiveTasks
- [ ] 2.6 T12 — 启用 Pinia Store：store/accounts.ts + store/tasks.ts
- [ ] 2.7 T13 — 无效 hotspot_id 显式错误：400 + invalid_ids 明细

## 3. P2 — 一致性、测试与 DB

- [ ] 3.1 T14 — 数据库迁移集成：启动脚本执行 migrations + create_all 降级
- [ ] 3.2 T15 — 拆分 models / schemas：包结构 + 全项目 import 更新
- [ ] 3.3 T16 — 后端测试补全：test_providers + test_scenario_configs + test_auth + conftest 修复
- [ ] 3.4 T17 — 重写 LLMService 测试：mock gateway + 删除 mock_mode 断言
- [ ] 3.5 T18 — 前端测试与 typecheck：router.test 重写 + format.ts 单测 + vue-tsc
- [ ] 3.6 T19 — 统一前端 UI 模式：PageHeader + v-loading + 修复硬编码
- [ ] 3.7 T20 — 合并重复 Adapter + 死代码清理：OpenAI 基类 + 删 generator mock
- [ ] 3.8 T21 — 常量与 Enum 集中：constants.py + enums.py
- [ ] 3.9 T22 — 结构化日志：logging_config.py + 替换 print()

## 4. P3 — 优化与文档

- [ ] 4.1 T23 — 任务 API 统一入口：评估 + ADR
- [ ] 4.2 T24 — 拆分 App 布局样式：styles/layout.css + components/layout/
- [ ] 4.3 T25 — CRUD 页抽象：useCrudDialog + 改造三页
- [ ] 4.4 T26 — 品牌与文档统一：「墨斋」命名 + README
- [ ] 4.5 T27 — Celery 重试与评审链健壮性：autoretry_for + 文档
