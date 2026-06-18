<!-- 加载顺序：AI agent 应先加载本文件，再加载 ../CLAUDE.md 获取全局约束 -->
<!-- 本文件中的内容为 ArticleGeneratorDatabase 独有；全局约定见 ../CLAUDE.md -->

# ArticleGeneratorDatabase — 数据库迁移

MySQL 表结构迁移脚本，按序号命名（`001_`、`002_`…）。

## 常用命令

### 执行迁移

```bash
cd ArticleGeneratorDatabase
# 迁移脚本位于 migrations/ 目录，按序号顺序执行
mysql -u root -p article_generator < migrations/001_initial_schema.sql
```

## 表结构概览（6 张表）

| 表 | 用途 | 关键字段 |
|----|------|----------|
| `hotspots` | 热点数据 | title, source, heat_score, url, status |
| `accounts` | 账号风格 | platform, account_name, lora_path, sample_articles |
| `articles` | 生成文章 | hotspot_id FK, account_id FK, content, status, refine_history JSON |
| `generation_tasks` | 生成任务 | task_id UNIQUE, status, article_id |
| `refine_tasks` | 微调任务 | task_id UNIQUE, article_id FK |
| `hotspot_sources` | 热点源配置 | name, type, config JSON, enabled |

## 迁移约定

- 脚本放在 `migrations/` 目录下
- 命名格式：`NNN_description.sql`（如 `001_initial_schema.sql`、`002_add_user_auth.sql`）
- 按序号升序执行，不可跳过
- 每次新增迁移需在 `migrations/README.md` 中记录变更说明

## 已知陷阱

### 数据库操作红线（不可绕过）

**禁止未经人工授权执行以下操作**（即使是开发环境 SQLite）：
- `rm` / `DROP TABLE` / `DELETE FROM` 删除数据库文件或数据
- 任何会导致数据丢失的操作

Schema 不匹配时必须使用 `ALTER TABLE` 迁移脚本或请求用户确认重建。参见 `migrations/` 目录下的现有迁移。

### CWD 依赖
后端 `DATABASE_URL` 使用相对路径时，SQLite 文件相对于 `ArticleGeneratorService/` 目录解析。本地开发与迁移脚本的 CWD 可能不一致。
