## ADDED Requirements

### Requirement: 每个服务拥有独立的 .claude/ 目录

项目中的每个服务模块 MUST 拥有独立的 `.claude/` 目录，用于存放服务级约束和配置文件。

服务级 `.claude/` 目录 SHALL 至少包含一个 `.gitkeep` 文件以确保被 git 追踪。

#### Scenario: AI agent 操作服务时需要服务级设置

- **WHEN** 某服务需要特定的 Claude Code 行为约束（如自定义 hook、权限配置）
- **THEN** 可在该服务的 `.claude/` 目录下创建 `settings.local.json`，不影响其他服务

#### Scenario: .claude/ 目录被 git 追踪

- **WHEN** 变更完成后运行 `git status`
- **THEN** 5 个服务的 `.claude/` 目录及其 `.gitkeep` 文件均出现在 tracked files 中

### Requirement: 文件覆盖 5 个服务模块

以下 5 个服务模块 MUST 各拥有 `.claude/` 目录：
- `ArticleGeneratorService/.claude/`
- `LLMService/.claude/`
- `ArticleGeneratorAdm/.claude/`
- `HotspotCrawler/.claude/`
- `ArticleGeneratorDatabase/.claude/`

#### Scenario: 所有服务 .claude/ 目录存在

- **WHEN** 变更完成后检查项目目录
- **THEN** 以上 5 个路径下均存在 `.claude/` 目录且包含 `.gitkeep` 文件
