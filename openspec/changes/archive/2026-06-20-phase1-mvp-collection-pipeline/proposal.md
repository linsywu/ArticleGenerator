## Why

千机笔系统目前具备 AI 创作能力（热点发现 → 风格蒸馏 → 文章生成 → 评审发布），但缺乏系统化的内容采集管道。对标公众号的文章数据无法自动入库，导致下游的素材中心、知识库中心、AI 分析中心全部阻塞。Phase 1 的目标是打通从「赛道定义 → 公众号注册 → 文章采集 → 素材入库」的完整数据管道，为后续模块提供数据基础。

## What Changes

- **新增** 赛道管理：一级赛道和二级赛道的 CRUD，支持热门关键词和禁用关键词配置，启停状态控制
- **新增** 公众号管理：采集目标公众号的注册和管理，支持公众号名称导入（调用 searchbiz 自动获取信息）和文章链接导入（解析 biz 参数）两种方式
- **新增** 采集凭证管理：微信公众号后台 token+cookie 凭证的存储、状态监控（normal/expiring_soon/expired/error）和有效性检测
- **新增** 采集任务管理：支持赛道+公众号多级选择配置采集范围，历史同步和增量同步两种模式，cron/interval/manual 三种执行方式
- **新增** 采集执行引擎：基于 Celery 的采集调度器和工作器，对接微信公众平台 appmsg/searchbiz 接口，包含防检测频次控制、URL+内容哈希去重、三级重试策略、采集日志记录
- **新增** 素材文章存储：采集的原始 HTML 入库，支持延迟解析（使用时才将 HTML 转为 Markdown），跳过图片处理
- **新增** 素材浏览页面：按赛道/公众号/时间范围筛选文章列表，详情页支持原文 HTML 和清洗后 Markdown 的 Tab 切换

## Capabilities

### New Capabilities

- `track-management`: 内容赛道分类体系管理，包含一级赛道和二级赛道的 CRUD、关键词配置、启停控制
- `mp-account-onboarding`: 采集目标公众号的接入管理，包含手动注册和两种自动导入方式（名称搜索、链接解析）
- `content-collection`: 公众号内容采集全流程，包含凭证管理、任务配置、调度执行、去重、重试、频率控制、日志记录
- `material-browsing`: 采集素材的浏览和检索，包含多维筛选、延迟解析（HTML→Markdown）、原文与清洗内容切换

### Modified Capabilities

<!-- No existing specs to modify. All capabilities are new. -->

## Impact

- **新增数据表 (7 张)**: tracks, sub_tracks, mp_accounts, mp_credentials, collect_tasks, mp_materials, collect_logs
- **新增后端 API 模块 (6 个)**: /api/tracks, /api/mp-accounts, /api/credentials, /api/collect-tasks, /api/materials, /api/collect-logs
- **新增前端页面 (5 个)**: TracksView, MpAccountsView, CredentialsView, CollectTasksView, MaterialsView
- **新增 Celery 任务**: 采集调度 (Celery Beat)、采集执行 (Worker)、凭证健康检测
- **新增依赖**: Turndown (HTML→Markdown 转换，Python 库)
- **不影响现有功能**: 所有新增表和 API 独立，不修改现有数据模型
