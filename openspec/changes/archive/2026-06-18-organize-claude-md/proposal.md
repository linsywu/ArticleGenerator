## Why

当前项目只有一个根目录 `CLAUDE.md`（~180 行），混合了全局架构概述和各模块细节。随着 5 个服务模块各自独立演进，单一文件无法有效承载模块级约束和上下文。AI agent 在操作具体服务时需要同时理解全局架构和模块细节，当前结构导致上下文膨胀和约束冲突。

## What Changes

- **拆分**根目录 `CLAUDE.md` 为全局概述（保留在根目录），移除各模块内部实现细节到对应服务的 `CLAUDE.md`
- **新增** 5 个服务级 `CLAUDE.md`：`ArticleGeneratorAdm/CLAUDE.md`、`ArticleGeneratorService/CLAUDE.md`、`LLMService/CLAUDE.md`、`HotspotCrawler/CLAUDE.md`、`ArticleGeneratorDatabase/CLAUDE.md`
- **新增** 各服务的 `.claude/` 目录结构，用于存放服务专属约束文件（settings、memory 等）
- **建立** `CLAUDE.md` 继承/引用规范：服务级 CLAUDE.md 开头引用根 CLAUDE.md，根 CLAUDE.md 末尾列出各服务入口

## Capabilities

### New Capabilities

- `service-claude-md`: 每个服务拥有独立的 CLAUDE.md，包含模块专用命令、架构、约束和陷阱
- `service-claude-dir`: 每个服务拥有独立的 `.claude/` 目录，用于管理服务级设置和约束

### Modified Capabilities

<!-- No existing specs to modify -->

## Impact

- 根 `CLAUDE.md`：内容精简 ~60%（从 ~180 行 → ~70 行），仅保留项目级概述和模块导航
- 5 个服务目录：各新增 `CLAUDE.md` + `.claude/` 骨架
- 无代码/API 变更，纯文档结构调整
