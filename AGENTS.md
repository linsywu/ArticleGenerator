# 项目公共规则配置

## 项目目录定义

| 目录 | 说明 |
|------|------|
| **HotspotCrawler** | 热点抓取模块（Scrapy/Requests + 定时任务） |
| **ArticleGeneratorAdm** | 管理后台前端代码（Vue/React + Element UI） |
| **ArticleGeneratorService** | 后端 API 代码（FastAPI + Celery） |
| **LLMService** | 模型服务（FastAPI 封装 LLM + LoRA） |
| **ArticleGeneratorDatabase** | 数据库相关设计文件（迁移脚本、ER 图等） |
| **.cursor/** | Cursor 配置：`plans/` 计划、`reports/` 验证报告、`rules/` 规则 |

---

## 核心能力

- **热点抓取**：定时从各行业获取热点，按热度排序，存入数据库
- **人工热点选择**：管理后台展示热点列表，运营人员多选热点并选择账号风格触发生成
- **智能文章生成**：基于选中热点，利用本地 LLM + LoRA 生成符合账号风格的文章
- **人工评审与微调**：待评审文章支持通过/拒绝，或输入关键词触发全文重写微调
- **人工发布辅助**：已通过文章可一键复制全文，人工粘贴发布后标记已发布

---

## 技术栈

| 模块 | 技术栈 | 说明 |
|------|--------|------|
| HotspotCrawler | Scrapy / Requests + BeautifulSoup / 免费 API | 热点抓取，定时任务 |
| ArticleGeneratorAdm | Vue / React + Element UI | 管理后台前端 |
| ArticleGeneratorService | FastAPI + SQLAlchemy + Celery | 后端 API、任务队列 |
| LLMService | FastAPI + 开源 LLM（ChatGLM3/Qwen）+ LoRA | 模型推理、多账号风格 |
| ArticleGeneratorDatabase | PostgreSQL / MySQL + Redis | 数据存储、缓存、消息队列 |

---

## 模块依赖关系

```
HotspotCrawler ──────┐
                     │
ArticleGeneratorAdm ─┼──HTTP──► ArticleGeneratorService ──HTTP──► LLMService
                     │                    │
                     │                    ▼
                     │         ArticleGeneratorDatabase
                     │
                     └──► Redis（Celery 消息队列）
```

- 管理后台与热点抓取均通过 HTTP 调用后端 API
- 后端 API 读写数据库，调用模型服务完成文章生成与微调
- Celery 消费 Redis 队列，异步执行生成任务

---

## 代码规范

- **注释语言**：中文
- **命名风格**：驼峰（camelCase），类/接口首字母大写
- **API 约定**：RESTful，JSON 请求/响应
- **组件化开发**：前端（如 Vue/Element Plus）页面逻辑和交互应尽量抽离为单独组件进行复用和维护，避免把所有逻辑堆积在一个超长文件。每个页面建议仅负责页面级逻辑，具体表单、对话框、表格项等抽出为 `components/` 下子组件，引入使用。
- **单一职责**：每个组件/文件只做一件事，文件长度建议不超过 200~300 行，复杂交互分拆处理，提升代码可读性和可维护性。
- **通用工具**：公用的数据校验、接口方法、工具函数、状态管理等应拆入 `utils/`、`api/` 或 `store/` 目录，页面和组件按需引入。
- **逻辑抽离**：公用的业务逻辑适度封装成 hooks 放在 `hooks/` 文件夹下面，便于复用。
- **命名规范**：组件、文件、方法、变量命名需意义明确，便于理解模块职责。

---

## 文件与路径约定

| 类型 | 位置 | 说明 |
|------|------|------|
| 环境变量 | 各模块根目录 `.env` 或 `config/` | 敏感配置不入库，提供 `.env.example` |
| 数据库脚本 | `ArticleGeneratorDatabase/migrations/` | 迁移脚本按序号执行 |
| AI 生成文档 | `.cursor/reports/` | 验证报告等 |
| 设计方案 | `docs/` | 设计文档、方案说明 |

---

## 开发协作约定

- **分支**：`main` 为主分支，功能分支 `feature/xxx`，修复分支 `fix/xxx`
- **提交**：语义化，如 `feat: 新增热点抓取`、`fix: 修正文章生成超时`
- **环境**：各模块 README 中说明本地运行与依赖安装

---

## AI 协作偏好

- **默认语言**：中文回复
- **代码生成**：在保证可读的前提下简洁，复杂逻辑需注释
- **生成文件位置**：见 `.cursor/rules/file-placement.mdc`，文档/报告一律放在项目内指定目录
