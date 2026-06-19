## ADDED Requirements

### Requirement: 每个服务拥有独立的 CLAUDE.md

项目中的每个服务模块 MUST 拥有独立的 `CLAUDE.md` 文件，包含该服务的专用指导信息。

服务级 `CLAUDE.md` 文件 SHALL 包含以下内容：
- 开头声明引用根 `CLAUDE.md`（`<!-- 继承自 ../CLAUDE.md -->`）
- 服务概述（1-2 句）
- 服务专用常用命令（启动、测试、调试）
- 服务架构详情（路由、组件、数据模型）
- 服务配置与环境变量
- 服务专属已知陷阱
- 不重复根 `CLAUDE.md` 中已有的全局信息

#### Scenario: AI agent 操作后端服务

- **WHEN** AI agent 被要求修改 `ArticleGeneratorService/` 中的代码
- **THEN** agent 应加载 `ArticleGeneratorService/CLAUDE.md` 获取服务专用上下文，再加载根 `CLAUDE.md` 获取全局架构

#### Scenario: 服务 CLAUDE.md 不包含全局信息

- **WHEN** 用户查看 `LLMService/CLAUDE.md`
- **THEN** 文件不重复根 `CLAUDE.md` 中的项目概述、通用命令或全局约定

### Requirement: 根 CLAUDE.md 作为项目级入口

项目根目录的 `CLAUDE.md` MUST 精简为项目级概述，包含：
- 项目概述和架构总览表
- 调用关系图
- 全局启动/停止命令
- 服务导航列表（链接到各服务 CLAUDE.md）
- 全局约定（提交格式、分支策略、文档位置）
- 跨服务陷阱

根 `CLAUDE.md` SHALL NOT 包含单个服务的详细路由表、专属测试命令或服务专属配置。

#### Scenario: 根 CLAUDE.md 精简

- **WHEN** 用户查看根 `CLAUDE.md`
- **THEN** 文件行数不超过 100 行（不含空白和注释），主要内容为架构导航和全局约定

### Requirement: 文件覆盖 5 个服务模块

以下 5 个服务模块 MUST 各拥有独立的 `CLAUDE.md`：
- `ArticleGeneratorService/CLAUDE.md` — 后端 API 服务
- `LLMService/CLAUDE.md` — LLM 推理服务
- `ArticleGeneratorAdm/CLAUDE.md` — 管理后台前端
- `HotspotCrawler/CLAUDE.md` — 热点抓取服务
- `ArticleGeneratorDatabase/CLAUDE.md` — 数据库迁移

#### Scenario: 所有服务 CLAUDE.md 存在

- **WHEN** 变更完成后检查项目目录
- **THEN** 以上 5 个路径下均存在非空的 `CLAUDE.md` 文件
