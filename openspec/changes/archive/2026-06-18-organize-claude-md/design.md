## Context

当前项目结构：5 个服务模块 + 1 个根 `CLAUDE.md`（~180 行），无服务级文档。AI agent 处理特定服务时需加载全部上下文。根 `.claude/` 目录已有 `skills/`、`worktrees/`、`agent-memory/`、`settings.local.json`。

约束：
- 不改变任何代码逻辑
- 不删除现有 `CLAUDE.md` 中的关键信息
- 保持中文注释风格
- 遵循项目已有的文档约定

## Goals / Non-Goals

**Goals:**
- 根 `CLAUDE.md` 精简为项目级概述（架构导航、全局命令、通用约定）
- 每个服务拥有独立的 `CLAUDE.md`，包含服务专用命令、架构、约束、陷阱
- 每个服务拥有独立的 `.claude/` 目录骨架
- 建立清晰的 CLAUDE.md 引用层级：服务级引用根级

**Non-Goals:**
- 不修改 `.claude/settings.json` 或 `settings.local.json` 内容
- 不移动或重组 `skills/`、`worktrees/` 目录
- 不创建新的项目级约束或流程
- 不涉及 `memory/` 相关配置

## Decisions

### 1. 文档分层策略：根 → 服务 → .claude/

```
ArticleGenerator/
├── CLAUDE.md                    ← 项目全局：架构导航、通用命令、通用约束
├── .claude/                     ← 项目全局：skills, worktrees, settings
├── ArticleGeneratorService/
│   ├── CLAUDE.md                ← 服务级：后端专用命令、路由、数据流、陷阱
│   └── .claude/                 ← 服务级：settings.local.json（可选）
├── LLMService/
│   ├── CLAUDE.md                ← 服务级：LLM 专用命令、模型配置、陷阱
│   └── .claude/
├── ArticleGeneratorAdm/
│   ├── CLAUDE.md                ← 服务级：前端专用命令、路由、组件约定、验证铁律
│   └── .claude/
├── HotspotCrawler/
│   ├── CLAUDE.md                ← 服务级：抓取专用命令、源配置、陷阱
│   └── .claude/
└── ArticleGeneratorDatabase/
    ├── CLAUDE.md                ← 服务级：迁移命令、表结构、迁移约定
    └── .claude/
```

**理由**：根 CLAUDE.md 作为入口索引，服务级 CLAUDE.md 承载模块上下文。AI agent 操作某服务时优先加载服务级 CLAUDE.md。

### 2. 根 CLAUDE.md 内容边界

保留：项目概述、架构总览表、调用关系图、通用命令、通用约定（提交格式、分支策略）、跨服务陷阱

移出到服务级：各服务启动命令、测试命令、路由表、服务专属陷阱和配置

**理由**：避免重复，根文件保持 ~70 行可快速扫读。

### 3. 服务级 CLAUDE.md 模板

每个服务 CLAUDE.md 开头包含引用声明：
```markdown
<!-- 继承自 ../CLAUDE.md，本文件覆盖服务专用内容 -->
```

然后包含：概述、常用命令（模块专属）、架构详情、配置、已知陷阱

### 4. .claude/ 目录初始内容

每个服务的 `.claude/` 初始仅包含一个 `.gitkeep` 文件（确保目录被 git 追踪）。后续可根据需要添加 `settings.local.json`。

**理由**：保持最小骨架，按需扩展。不预创建空配置文件。

## Risks / Trade-offs

- **[信息同步风险]** 根 CLAUDE.md 和服务 CLAUDE.md 可能有重复信息 → 采用引用层级，服务级不重复根级内容，通过开头引用声明确保 AI agent 知道加载顺序
- **[文件增长风险]** 6 个 CLAUDE.md 文件可能难以维护 → 仅服务级文件包含可执行命令和动态陷阱，根级内容相对静态
