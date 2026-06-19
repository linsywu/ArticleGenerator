## 1. 目录结构初始化

- [ ] 1.1 在各服务目录下创建 `.claude/` 目录（5 个服务）
- [ ] 1.2 在每个 `.claude/` 目录下创建 `.gitkeep` 文件

## 2. 根 CLAUDE.md 重构

- [ ] 2.1 精简根 `CLAUDE.md`：移除服务专属命令和路由细节，保留项目级架构概述、全局命令、通用约定、跨服务陷阱，添加服务导航表

## 3. 服务 CLAUDE.md 创建

- [ ] 3.1 创建 `ArticleGeneratorService/CLAUDE.md`：后端 API 专用命令、路由表、Celery 任务架构、数据库表详情、配置
- [ ] 3.2 创建 `LLMService/CLAUDE.md`：LLM 推理专用命令、模型配置、Mock 模式、Adapter 注册陷阱、CrazyRouter 模型映射
- [ ] 3.3 创建 `ArticleGeneratorAdm/CLAUDE.md`：前端专用命令、页面路由、组件约定、Vite 代理、前端验证铁律、测试限制
- [ ] 3.4 创建 `HotspotCrawler/CLAUDE.md`：热点抓取专用命令、源配置、API 调用格式
- [ ] 3.5 创建 `ArticleGeneratorDatabase/CLAUDE.md`：迁移命令、表结构概览、迁移约定

## 4. 验证

- [ ] 4.1 确认 5 个服务均有 `CLAUDE.md` + `.claude/.gitkeep`，根 `CLAUDE.md` 已精简
- [ ] 4.2 确认 git status 显示所有新文件已追踪
