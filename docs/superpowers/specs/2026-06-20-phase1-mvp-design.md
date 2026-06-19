# Phase 1 MVP Design: 数据采集底座

> **Status:** Approved | **Date:** 2026-06-20 | **Scope:** 赛道管理 + 公众号管理 + 内容采集中心

## 1. Overview

### What

打通千机笔系统的数据管道：从「赛道定义 → 公众号注册 → 文章采集 → 素材入库」的完整链路。这是 PRD 中所有下游模块（素材中心、知识库、AI分析、创作增强）的数据基础。

### Why This Scope

- 采集是阻塞点：素材中心、知识库、AI分析全部依赖采集的数据
- 赛道 + 公众号是采集的前置依赖（采集任务按赛道+公众号配置）
- 已有系统的热点+创作线可与采集并行开发，互不阻塞

### Modules (3)

| # | Module | Tables | Complexity |
|---|--------|--------|-------------|
| 1 | 赛道管理 | tracks, sub_tracks | Low (CRUD) |
| 2 | 公众号管理 | mp_accounts | Medium (CRUD + 2 import methods) |
| 3 | 内容采集中心 | mp_credentials, collect_tasks, collect_logs, mp_materials | High (Scheduler + Worker + Parser) |

## 2. Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                   Existing System                             │
│  FastAPI (ArticleGeneratorService)                           │
│  ├─ /api/accounts, /api/articles, /api/generate, ...         │
│  ├─ Celery (CeleryApp + tasks)                               │
│  └─ SQLAlchemy models (accounts, articles, hotspots, ...)    │
│                                                              │
│  LLM Gateway (LLMService)                                    │
│  HotspotCrawler                                              │
│  Vue 3 Frontend (ArticleGeneratorAdm)                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ NEW: Phase 1 adds
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend: New API modules                                    │
│  ├─ /api/tracks          — CRUD for tracks & sub_tracks      │
│  ├─ /api/mp-accounts     — CRUD + import for mp_accounts     │
│  ├─ /api/credentials     — CRUD for mp_credentials           │
│  ├─ /api/collect-tasks   — CRUD for collect_tasks            │
│  ├─ /api/materials       — List + detail for mp_materials    │
│  └─ /api/collect-logs    — Read-only for collect_logs        │
│                                                              │
│  Collector Engine (Celery-based)                             │
│  ├─ CollectorScheduler   — Celery Beat periodic tasks        │
│  ├─ CollectorWorker      — Celery task: execute collection   │
│  ├─ MpClient             — HTTP client for wechat MP API     │
│  └─ Parser (lazy)        — HTML→Markdown on demand           │
│                                                              │
│  Frontend: New pages                                         │
│  ├─ TracksView.vue       — 赛道列表 + 新增/编辑 Modal         │
│  ├─ MpAccountsView.vue   — 公众号列表 + 导入 Modal            │
│  ├─ CredentialsView.vue  — 凭证管理                           │
│  ├─ CollectTasksView.vue — 采集任务管理                       │
│  └─ MaterialsView.vue    — 素材列表（基础版）                  │
└─────────────────────────────────────────────────────────────┘
```

### Integration with Existing System

- **No changes to existing tables** — all new tables, no migrations on existing
- **Reuse Celery infrastructure** — same Celery app (`ArticleGeneratorService/app/tasks.py`), add new tasks
- **Follow existing API patterns** — same FastAPI router structure, same auth (JWT), same error handling
- **Frontend follows existing patterns** — Vue 3 + Element Plus + `src/api/modules/*.ts` + `src/views/*.vue`

## 3. Data Models

### 3.1 tracks (一级赛道)

```sql
CREATE TABLE tracks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    keywords JSON COMMENT '热门关键词数组',
    forbidden_keywords JSON COMMENT '禁用关键词数组',
    status TINYINT DEFAULT 1 COMMENT '0=禁用 1=启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.2 sub_tracks (二级赛道)

```sql
CREATE TABLE sub_tracks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    track_id BIGINT NOT NULL COMMENT '关联一级赛道',
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE,
    INDEX idx_track (track_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.3 mp_accounts (公众号)

```sql
CREATE TABLE mp_accounts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '公众号名称',
    alias VARCHAR(100) COMMENT '微信号',
    fakeid VARCHAR(100) COMMENT '公众号fakeid',
    biz VARCHAR(100) COMMENT 'biz参数',
    avatar VARCHAR(500) COMMENT '头像URL',
    description TEXT COMMENT '简介',
    track_ids JSON COMMENT '所属赛道ID数组',
    article_count INT DEFAULT 0 COMMENT '已采集文章数',
    last_collect_time DATETIME COMMENT '最后采集时间',
    status TINYINT DEFAULT 1 COMMENT '0=停用 1=正常',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_fakeid (fakeid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.4 mp_credentials (采集凭证)

```sql
CREATE TABLE mp_credentials (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '凭证名称',
    token VARCHAR(500) NOT NULL COMMENT '公众号token',
    cookie TEXT NOT NULL COMMENT '公众号cookie',
    status VARCHAR(20) DEFAULT 'normal' COMMENT 'normal/expiring_soon/expired/error',
    check_time DATETIME COMMENT '最后检测时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.5 collect_tasks (采集任务)

```sql
CREATE TABLE collect_tasks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '任务名称',
    credential_id BIGINT NOT NULL COMMENT '使用的凭证',
    track_ids JSON COMMENT '目标赛道ID数组',
    account_ids JSON COMMENT '目标公众号ID数组(空=赛道全采)',
    collect_mode VARCHAR(30) NOT NULL COMMENT 'history_50/history_100/history_200/date_range/incremental',
    date_start DATE COMMENT 'date_range模式: 开始日期',
    date_end DATE COMMENT 'date_range模式: 结束日期',
    schedule_type VARCHAR(20) DEFAULT 'manual' COMMENT 'manual/interval/cron',
    cron VARCHAR(50) COMMENT 'cron表达式',
    interval_hours INT COMMENT 'interval模式: 间隔小时数',
    status VARCHAR(20) DEFAULT 'idle' COMMENT 'idle/running/paused/error',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (credential_id) REFERENCES mp_credentials(id) ON DELETE RESTRICT,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.6 mp_materials (素材文章)

```sql
CREATE TABLE mp_materials (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT NOT NULL COMMENT '来源公众号',
    title VARCHAR(500) COMMENT '文章标题',
    author VARCHAR(100) COMMENT '作者',
    original_url VARCHAR(1000) NOT NULL COMMENT '原文链接',
    cover_url VARCHAR(500) COMMENT '封面图URL',
    summary TEXT COMMENT '摘要',
    raw_html LONGTEXT COMMENT '原始HTML(采集时存入)',
    content_markdown LONGTEXT COMMENT '清洗后Markdown(延迟解析)',
    content_hash VARCHAR(64) COMMENT 'SHA256去重',
    word_count INT DEFAULT 0 COMMENT '字数',
    is_original TINYINT DEFAULT 0 COMMENT '是否原创标识',
    published_at DATETIME COMMENT '文章发布时间',
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES mp_accounts(id) ON DELETE CASCADE,
    UNIQUE KEY uk_original_url (original_url(500)),
    INDEX idx_account (account_id),
    INDEX idx_published (published_at DESC),
    INDEX idx_content_hash (content_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3.7 collect_logs (采集日志)

```sql
CREATE TABLE collect_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT NOT NULL COMMENT '关联采集任务',
    account_id BIGINT COMMENT '目标公众号',
    start_time DATETIME,
    end_time DATETIME,
    total_count INT DEFAULT 0 COMMENT '发现文章数',
    success_count INT DEFAULT 0 COMMENT '成功入库数',
    fail_count INT DEFAULT 0 COMMENT '失败数',
    error_message JSON COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES collect_tasks(id) ON DELETE CASCADE,
    INDEX idx_task (task_id),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 4. API Design

### 4.1 Tracks API (`/api/tracks`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tracks` | 一级赛道列表 (支持 search, status 筛选) |
| POST | `/api/tracks` | 新增一级赛道 |
| GET | `/api/tracks/{id}` | 一级赛道详情 (含二级赛道列表) |
| PUT | `/api/tracks/{id}` | 编辑一级赛道 |
| PATCH | `/api/tracks/{id}/status` | 启停一级赛道 |
| DELETE | `/api/tracks/{id}` | 删除一级赛道 (级联删除二级) |
| POST | `/api/tracks/{id}/sub-tracks` | 新增二级赛道 |
| PUT | `/api/sub-tracks/{id}` | 编辑二级赛道 |
| DELETE | `/api/sub-tracks/{id}` | 删除二级赛道 |

### 4.2 MP Accounts API (`/api/mp-accounts`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/mp-accounts` | 公众号列表 (支持 track_id, status, search 筛选, 分页) |
| POST | `/api/mp-accounts` | 手动新增公众号 |
| GET | `/api/mp-accounts/{id}` | 公众号详情 |
| PUT | `/api/mp-accounts/{id}` | 编辑公众号 |
| PATCH | `/api/mp-accounts/{id}/status` | 启停公众号 |
| DELETE | `/api/mp-accounts/{id}` | 删除公众号 |
| POST | `/api/mp-accounts/import-by-name` | 名称导入 (body: names[], 触发 searchbiz) |
| POST | `/api/mp-accounts/import-by-url` | 链接导入 (body: urls[], 解析biz参数) |

### 4.3 Credentials API (`/api/credentials`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/credentials` | 凭证列表 |
| POST | `/api/credentials` | 新增凭证 |
| PUT | `/api/credentials/{id}` | 编辑凭证 |
| DELETE | `/api/credentials/{id}` | 删除凭证 |
| POST | `/api/credentials/{id}/check` | 手动检测凭证有效性 |

### 4.4 Collect Tasks API (`/api/collect-tasks`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/collect-tasks` | 任务列表 (支持 status 筛选) |
| POST | `/api/collect-tasks` | 新建任务 |
| GET | `/api/collect-tasks/{id}` | 任务详情 |
| PUT | `/api/collect-tasks/{id}` | 编辑任务 |
| DELETE | `/api/collect-tasks/{id}` | 删除任务 |
| POST | `/api/collect-tasks/{id}/execute` | 手动执行任务 |
| POST | `/api/collect-tasks/{id}/pause` | 暂停定时任务 |
| POST | `/api/collect-tasks/{id}/resume` | 恢复定时任务 |

### 4.5 Materials API (`/api/materials`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/materials` | 素材列表 (支持 track_id, account_id, date range, search 筛选, 分页) |
| GET | `/api/materials/{id}` | 素材详情 (含 raw_html, content_markdown) |
| POST | `/api/materials/{id}/parse` | 触发解析 (HTML→Markdown，若未解析) |

### 4.6 Collect Logs API (`/api/collect-logs`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/collect-logs` | 日志列表 (支持 task_id, account_id 筛选, 分页) |
| GET | `/api/collect-logs/{id}` | 日志详情 |

## 5. Collection Engine Design

### 5.1 Architecture

```
Celery Beat (scheduler)
    │  periodic: scan collect_tasks for ready tasks
    │  match cron/interval → dispatch
    ▼
Celery Worker: execute_collect_task(task_id)
    │
    ├─ 1. Credential pre-check
    │     load mp_credentials → if status in (expired, error) → abort + alert
    │
    ├─ 2. Resolve target accounts
    │     if account_ids set → use directly
    │     else → query mp_accounts WHERE track_ids overlaps
    │
    ├─ 3. For each account: (serial, with rate limiting)
    │     ├─ Frequency check: last_collect_time < 24h ago? → skip
    │     ├─ Wait: global interval ≥15s + random jitter
    │     ├─ MpClient.fetch_article_list(fakeid, credential, mode)
    │     │     GET /cgi-bin/appmsg?fakeid=xxx&begin=0&count=10
    │     │     → parse app_msg_list → article URLs
    │     ├─ For each new URL (dedup by uk_original_url):
    │     │     ├─ Wait: domain interval ≥20-30s
    │     │     ├─ HTTP GET article URL → raw HTML
    │     │     ├─ Extract: title, author, published_at from HTML meta
    │     │     ├─ SHA256(raw_html) → content_hash
    │     │     ├─ Dedup: content_hash exists? → skip
    │     │     └─ INSERT INTO mp_materials
    │     └─ UPDATE mp_accounts SET last_collect_time = now(), article_count = ...
    │
    ├─ 4. Write collect_log
    │     INSERT INTO collect_logs (task_id, account_id, start/end, counts, errors)
    │
    └─ 5. Update task status → idle (or next scheduled run)
```

### 5.2 Rate Limiting (Anti-Detection)

| Dimension | Limit | Reason |
|-----------|-------|--------|
| Global request interval | ≥15s + random jitter (±5s) | Simulate human reading rhythm |
| Same-domain interval | ≥20-30s | mp.weixin.qq.com consecutive requests |
| Per-account collection interval | ≥24h | Low-frequency daily collection |
| Max articles per account per run | 200 | Prevent excessive historical sync |
| Concurrent workers | ≤2 | Avoid concurrent fingerprint |

### 5.3 Credential Health Check

- **Scheduled:** Celery Beat task every 6 hours
  - Use token+cookie to call searchbiz with a known account name
  - Check response status code
  - Normal → keep `normal`
  - Abnormal → mark `expiring_soon`
  - Consecutive failures → mark `expired`

- **Pre-task:** Before each collection task starts
  - `normal` → proceed
  - `expiring_soon` → proceed but emit warning
  - `expired` / `error` → abort, notify frontend

### 5.4 Dedup Strategy

1. **URL dedup** — `original_url` unique index (first line of defense, fastest)
2. **Content dedup** — `content_hash` SHA256 comparison (same content, different URLs)
3. **Title similarity** — optional, for future enhancement

### 5.5 Retry Strategy

| Attempt | Delay | Behavior |
|---------|-------|----------|
| 1st | 10 min | Auto retry |
| 2nd | 30 min | Auto retry |
| 3rd | 60 min | Auto retry |
| Final | — | Mark article as failed in log, continue to next article |

### 5.6 Lazy Parsing

- Collection stores **raw HTML only** (and extracted metadata: title, author, published_at)
- `content_markdown` is NULL until first access
- Triggered by: `POST /api/materials/{id}/parse` or auto-triggered on `GET /api/materials/{id}` if markdown is NULL
- Parse flow: raw_html → Turndown (HTML→Markdown) → save to content_markdown → cache for future reads
- Image processing: **skipped** (not valuable for third-party article reference)

## 6. Frontend Pages

### 6.1 TracksView — 赛道管理

- **Route:** `/tracks`
- **Layout:** Table list + inline expand for sub-tracks
- **Actions:** Add/Edit track (modal), toggle status, delete
- **Sub-track management:** Expand row → list sub-tracks → add/edit/delete inline

### 6.2 MpAccountsView — 公众号管理

- **Route:** `/mp-accounts`
- **Layout:** Table list with filters (track, status, search)
- **Actions:** Add (manual), Import (modal with name/url tabs), Edit, toggle, Delete
- **Import modal:** Two tabs — "名称导入" (textarea + submit) & "链接导入" (textarea + submit)

### 6.3 CredentialsView — 凭证管理

- **Route:** `/credentials`
- **Layout:** Card list showing name, status badge, check_time
- **Actions:** Add, Edit, Delete, "检测" button to manually trigger health check
- **Status display:** Colored badge (green=normal, yellow=expiring_soon, red=expired, purple=error)

### 6.4 CollectTasksView — 采集任务

- **Route:** `/collect-tasks`
- **Layout:** Table list with status column
- **Actions:** Add, Edit, Delete, Execute (manual trigger), Pause/Resume
- **Add/Edit form:**
  - Multi-level selector: Track → expand → check/uncheck individual accounts
  - Collect mode dropdown
  - Schedule type selector with cron input or interval input
  - Credential selector

### 6.5 MaterialsView — 素材列表

- **Route:** `/materials`
- **Layout:** Table list with filters (track, account, date range, search)
- **Detail view:** Tabs for HTML preview and Markdown (lazy-parsed)
- **Per-row action:** "💡 创作方向" button → triggers argument storm (Phase 3 feature, placeholder for now)

### Navigation Updates

Add to `LayoutView.vue` sidebar:
```
赛道管理     /tracks
公众号管理   /mp-accounts
采集凭证     /credentials
采集任务     /collect-tasks
素材中心     /materials
```

## 7. Implementation Order (within Phase 1)

```
Step 1: 赛道管理 (1-2 days)
  ├─ Migration: tracks + sub_tracks tables
  ├─ Backend: /api/tracks CRUD
  ├─ Frontend: TracksView.vue
  └─ Test: CRUD + status toggle + cascade delete

Step 2: 公众号基础管理 (2-3 days)
  ├─ Migration: mp_accounts table
  ├─ Backend: /api/mp-accounts CRUD (without import)
  ├─ Frontend: MpAccountsView.vue (without import modal)
  └─ Test: CRUD + track filtering

Step 3: 采集凭证管理 (1 day)
  ├─ Migration: mp_credentials table
  ├─ Backend: /api/credentials CRUD + check endpoint
  ├─ Frontend: CredentialsView.vue
  └─ Test: CRUD + manual check

Step 4: 采集任务管理 (2-3 days)
  ├─ Migration: collect_tasks table
  ├─ Backend: /api/collect-tasks CRUD + execute
  ├─ Frontend: CollectTasksView.vue (with multi-level selector)
  └─ Test: CRUD + manual execute

Step 5: 采集执行引擎 (3-5 days)
  ├─ Migration: mp_materials + collect_logs tables
  ├─ Backend: MpClient (HTTP client for WeChat MP API)
  ├─ Backend: CollectorWorker (Celery task)
  ├─ Backend: CollectorScheduler (Celery Beat config)
  ├─ Backend: Rate limiter + dedup + retry logic
  └─ Test: End-to-end collection flow

Step 6: 素材列表 (1-2 days)
  ├─ Backend: /api/materials list + detail + parse
  ├─ Frontend: MaterialsView.vue
  └─ Test: List filtering + detail tabs + lazy parse

Step 7: 公众号导入 (1-2 days)
  ├─ Backend: /api/mp-accounts/import-by-name + import-by-url
  ├─ Frontend: Import modal in MpAccountsView.vue
  └─ Test: Name import + URL import + error handling
```

**Total estimate:** ~12-18 days for complete Phase 1 MVP

## 8. Testing Strategy

- **Backend:** Follow existing test patterns (`ArticleGeneratorService/tests/`)
  - API endpoint tests (CRUD + edge cases)
  - Collector unit tests (MpClient mock, dedup logic)
- **Frontend:** Manual verification (per verification rule in memory)
  - Start dev server, visit each new page
  - Test CRUD operations, filters, modals
  - Test import flows (when implemented)

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| WeChat MP API changes (appmsg/searchbiz) | MpClient isolated behind interface, easy to adapt |
| Credential expiration during collection | Pre-task check + health monitoring every 6h |
| Rate limiting → slow collection | Acceptable: low-frequency daily use case |
| Large HTML storage (raw_html longtext) | Lazy parse to markdown, consider compression later |
