# Phase 1 MVP: 数据采集底座 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete data collection pipeline: track management → MP account onboarding → collection engine → material browsing.

**Architecture:** New tables (tracks, sub_tracks, mp_accounts, mp_credentials, collect_tasks, mp_materials, collect_logs) + new API modules following existing FastAPI patterns + Celery-based collector engine + Vue 3 frontend pages following existing component patterns. All additions are independent of existing tables/APIs — no modifications to current system.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, Celery, Pydantic, Vue 3, TypeScript, Element Plus

---

## 1. Database Migrations

**Files:**
- Create: `ArticleGeneratorDatabase/migrations/008_create_tracks.sql`
- Create: `ArticleGeneratorDatabase/migrations/009_create_mp_accounts.sql`
- Create: `ArticleGeneratorDatabase/migrations/010_create_mp_credentials.sql`
- Create: `ArticleGeneratorDatabase/migrations/011_create_collect_tasks.sql`
- Create: `ArticleGeneratorDatabase/migrations/012_create_mp_materials.sql`
- Create: `ArticleGeneratorDatabase/migrations/013_create_collect_logs.sql`

### Task 1.1: Create tracks + sub_tracks migration

- [ ] **Step 1: Write migration 008**

```sql
-- 008_create_tracks.sql
-- 赛道管理：一级赛道 + 二级赛道
-- SQLite-compatible (no MySQL COMMENT syntax)

CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    keywords TEXT,
    forbidden_keywords TEXT,
    status INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sub_tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE,
    INDEX idx_track (track_id)
);
```

- [ ] **Step 2: Run migration against dev DB**

```bash
cd ArticleGeneratorDatabase && python -c "
import sqlite3
conn = sqlite3.connect('dev.db')
with open('migrations/008_create_tracks.sql') as f:
    conn.executescript(f.read())
conn.close()
print('Migration 008 applied')
"
```

- [ ] **Step 3: Verify tables exist**

```bash
cd ArticleGeneratorDatabase && python -c "
import sqlite3
conn = sqlite3.connect('dev.db')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name IN ('tracks', 'sub_tracks')\").fetchall()
print('Tables:', [t[0] for t in tables])
conn.close()
"
```
Expected: `Tables: ['tracks', 'sub_tracks']`

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorDatabase/migrations/008_create_tracks.sql
git commit -m "feat: add tracks and sub_tracks tables migration"
```

### Task 1.2: Create mp_accounts migration

- [ ] **Step 1: Write migration 009**

```sql
-- 009_create_mp_accounts.sql
CREATE TABLE IF NOT EXISTS mp_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    alias VARCHAR(100),
    fakeid VARCHAR(100),
    biz VARCHAR(100),
    avatar VARCHAR(500),
    description TEXT,
    track_ids TEXT,
    article_count INTEGER DEFAULT 0,
    last_collect_time DATETIME,
    status INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mp_accounts_status ON mp_accounts(status);
CREATE INDEX IF NOT EXISTS idx_mp_accounts_fakeid ON mp_accounts(fakeid);
```

- [ ] **Step 2: Apply and verify**

```bash
cd ArticleGeneratorDatabase && python -c "
import sqlite3
conn = sqlite3.connect('dev.db')
with open('migrations/009_create_mp_accounts.sql') as f:
    conn.executescript(f.read())
r = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='mp_accounts'\").fetchone()
print('Table created:', r is not None)
conn.close()
"
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorDatabase/migrations/009_create_mp_accounts.sql
git commit -m "feat: add mp_accounts table migration"
```

### Task 1.3: Create mp_credentials migration

- [ ] **Step 1: Write migration 010**

```sql
-- 010_create_mp_credentials.sql
CREATE TABLE IF NOT EXISTS mp_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    token VARCHAR(500) NOT NULL,
    cookie TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'normal',
    check_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mp_cred_status ON mp_credentials(status);
```

- [ ] **Step 2: Apply, verify, commit**

```bash
cd ArticleGeneratorDatabase && python -c "
import sqlite3; conn = sqlite3.connect('dev.db')
with open('migrations/010_create_mp_credentials.sql') as f: conn.executescript(f.read())
print('mp_credentials:', conn.execute(\"SELECT name FROM sqlite_master WHERE name='mp_credentials'\").fetchone() is not None)
conn.close()
"
```

```bash
git add ArticleGeneratorDatabase/migrations/010_create_mp_credentials.sql
git commit -m "feat: add mp_credentials table migration"
```

### Task 1.4: Create collect_tasks migration

- [ ] **Step 1: Write migration 011**

```sql
-- 011_create_collect_tasks.sql
CREATE TABLE IF NOT EXISTS collect_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    credential_id INTEGER NOT NULL,
    track_ids TEXT,
    account_ids TEXT,
    collect_mode VARCHAR(30) NOT NULL DEFAULT 'incremental',
    date_start DATE,
    date_end DATE,
    schedule_type VARCHAR(20) DEFAULT 'manual',
    cron VARCHAR(50),
    interval_hours INTEGER,
    status VARCHAR(20) DEFAULT 'idle',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (credential_id) REFERENCES mp_credentials(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_collect_tasks_status ON collect_tasks(status);
```

- [ ] **Step 2: Apply, verify, commit**

```bash
git add ArticleGeneratorDatabase/migrations/011_create_collect_tasks.sql
git commit -m "feat: add collect_tasks table migration"
```

### Task 1.5: Create mp_materials migration

- [ ] **Step 1: Write migration 012**

```sql
-- 012_create_mp_materials.sql
CREATE TABLE IF NOT EXISTS mp_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    title VARCHAR(500),
    author VARCHAR(100),
    original_url VARCHAR(1000) NOT NULL,
    cover_url VARCHAR(500),
    summary TEXT,
    raw_html TEXT,
    content_markdown TEXT,
    content_hash VARCHAR(64),
    word_count INTEGER DEFAULT 0,
    is_original INTEGER DEFAULT 0,
    published_at DATETIME,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES mp_accounts(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_mp_materials_url ON mp_materials(original_url);
CREATE INDEX IF NOT EXISTS idx_mp_materials_account ON mp_materials(account_id);
CREATE INDEX IF NOT EXISTS idx_mp_materials_published ON mp_materials(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_mp_materials_hash ON mp_materials(content_hash);
```

- [ ] **Step 2: Apply, verify, commit**

```bash
git add ArticleGeneratorDatabase/migrations/012_create_mp_materials.sql
git commit -m "feat: add mp_materials table migration"
```

### Task 1.6: Create collect_logs migration

- [ ] **Step 1: Write migration 013**

```sql
-- 013_create_collect_logs.sql
CREATE TABLE IF NOT EXISTS collect_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    account_id INTEGER,
    start_time DATETIME,
    end_time DATETIME,
    total_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES collect_tasks(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_collect_logs_task ON collect_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_collect_logs_created ON collect_logs(created_at DESC);
```

- [ ] **Step 2: Apply, verify, commit**

```bash
git add ArticleGeneratorDatabase/migrations/013_create_collect_logs.sql
git commit -m "feat: add collect_logs table migration"
```

---

## 2. Track Management Backend

**Files:**
- Modify: `ArticleGeneratorService/app/models.py` — add Track, SubTrack
- Modify: `ArticleGeneratorService/app/schemas.py` — add track schemas
- Create: `ArticleGeneratorService/app/api/tracks.py`
- Modify: `ArticleGeneratorService/app/main.py` — register router

### Task 2.1: Add Track + SubTrack models

- [ ] **Step 1: Add models to models.py (after existing models, before EOF)**

```python
class Track(Base):
    """一级赛道"""
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    keywords = Column(Text)  # JSON string
    forbidden_keywords = Column(Text)  # JSON string
    status = Column(Integer, default=1)  # 0=禁用 1=启用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sub_tracks = relationship("SubTrack", back_populates="track", cascade="all, delete-orphan")


class SubTrack(Base):
    """二级赛道"""
    __tablename__ = "sub_tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    track = relationship("Track", back_populates="sub_tracks")
```

- [ ] **Step 2: Run backend to verify models load without error**

```bash
cd ArticleGeneratorService && python -c "from app.models import Track, SubTrack; print('Models loaded OK')"
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/models.py
git commit -m "feat: add Track and SubTrack SQLAlchemy models"
```

### Task 2.2: Add Track Pydantic schemas

- [ ] **Step 1: Add to schemas.py (after existing schemas, before EOF)**

```python
# ----- 赛道 -----
class SubTrackBase(BaseModel):
    name: str
    description: Optional[str] = None

class SubTrackCreate(SubTrackBase): pass

class SubTrackResponse(SubTrackBase):
    id: int
    track_id: int
    created_at: datetime
    class Config: from_attributes = True

class TrackBase(BaseModel):
    name: str
    description: Optional[str] = None
    keywords: Optional[str] = None
    forbidden_keywords: Optional[str] = None

class TrackCreate(TrackBase): pass

class TrackUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[str] = None
    forbidden_keywords: Optional[str] = None

class TrackResponse(TrackBase):
    id: int
    status: int = 1
    sub_tracks: List[SubTrackResponse] = []
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True
```

- [ ] **Step 2: Verify schemas load**

```bash
cd ArticleGeneratorService && python -c "from app.schemas import TrackCreate, TrackResponse; print('Track schemas OK')"
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/schemas.py
git commit -m "feat: add Track and SubTrack Pydantic schemas"
```

### Task 2.3: Create tracks API module

- [ ] **Step 1: Write a failing API test (TDD)**

```python
# ArticleGeneratorService/tests/test_api_tracks.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, init_db, SessionLocal
from app.auth import create_access_token
from app.models import Base, User
from app.auth import get_password_hash

@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def auth_headers(client):
    # Ensure seed user exists and get token
    db = SessionLocal()
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        user = User(username="admin", password_hash=get_password_hash("admin123"))
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token(data={"sub": user.username})
    db.close()
    return {"Authorization": f"Bearer {token}"}

def test_create_track(client, auth_headers):
    resp = client.post("/api/tracks", json={
        "name": "AI科技",
        "description": "AI行业资讯",
        "keywords": '["AI", "ChatGPT"]',
        "forbidden_keywords": '["赌博"]'
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "AI科技"
    assert data["status"] == 1

def test_list_tracks(client, auth_headers):
    resp = client.get("/api/tracks", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1

def test_toggle_track_status(client, auth_headers):
    # Create a track first
    create_resp = client.post("/api/tracks", json={"name": "Test"}, headers=auth_headers)
    track_id = create_resp.json()["id"]
    # Disable it
    patch_resp = client.patch(f"/api/tracks/{track_id}/status", json={"status": 0}, headers=auth_headers)
    assert patch_resp.status_code == 200
    # Verify
    get_resp = client.get(f"/api/tracks/{track_id}", headers=auth_headers)
    assert get_resp.json()["status"] == 0

def test_create_sub_track(client, auth_headers):
    create_resp = client.post("/api/tracks", json={"name": "Parent Track"}, headers=auth_headers)
    track_id = create_resp.json()["id"]
    sub_resp = client.post(f"/api/tracks/{track_id}/sub-tracks", json={
        "name": "大模型", "description": "LLM相关"
    }, headers=auth_headers)
    assert sub_resp.status_code == 200
    assert sub_resp.json()["name"] == "大模型"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ArticleGeneratorService && python -m pytest tests/test_api_tracks.py -v
```
Expected: FAIL with 404 (router not registered yet)

- [ ] **Step 3: Write tracks.py API module**

```python
"""
赛道管理 API
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Track, SubTrack
from ..schemas import TrackCreate, TrackUpdate, TrackResponse, SubTrackCreate, SubTrackResponse
from ..deps import get_current_user

router = APIRouter(prefix="/tracks", tags=["赛道管理"])


@router.get("", response_model=List[TrackResponse])
def list_tracks(db: Session = Depends(get_db)):
    """获取一级赛道列表（含二级赛道）"""
    return db.query(Track).order_by(Track.id.desc()).all()


@router.post("", response_model=TrackResponse)
def create_track(data: TrackCreate, db: Session = Depends(get_db)):
    """新增一级赛道"""
    track = Track(**data.model_dump())
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


@router.get("/{track_id}", response_model=TrackResponse)
def get_track(track_id: int, db: Session = Depends(get_db)):
    """获取赛道详情（含二级赛道列表）"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="赛道不存在")
    return track


@router.put("/{track_id}", response_model=TrackResponse)
def update_track(track_id: int, data: TrackUpdate, db: Session = Depends(get_db)):
    """编辑赛道"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="赛道不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(track, k, v)
    db.commit()
    db.refresh(track)
    return track


@router.patch("/{track_id}/status")
def toggle_track_status(track_id: int, data: dict, db: Session = Depends(get_db)):
    """启停赛道"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="赛道不存在")
    track.status = data.get("status", track.status)
    db.commit()
    return {"message": "状态已更新"}


@router.delete("/{track_id}")
def delete_track(track_id: int, db: Session = Depends(get_db)):
    """删除赛道（级联删除二级赛道）"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="赛道不存在")
    db.delete(track)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{track_id}/sub-tracks", response_model=SubTrackResponse)
def create_sub_track(track_id: int, data: SubTrackCreate, db: Session = Depends(get_db)):
    """新增二级赛道"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="赛道不存在")
    sub = SubTrack(track_id=track_id, **data.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.put("/sub-tracks/{sub_track_id}", response_model=SubTrackResponse)
def update_sub_track(sub_track_id: int, data: SubTrackCreate, db: Session = Depends(get_db)):
    """编辑二级赛道"""
    sub = db.query(SubTrack).filter(SubTrack.id == sub_track_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="二级赛道不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(sub, k, v)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/sub-tracks/{sub_track_id}")
def delete_sub_track(sub_track_id: int, db: Session = Depends(get_db)):
    """删除二级赛道"""
    sub = db.query(SubTrack).filter(SubTrack.id == sub_track_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="二级赛道不存在")
    db.delete(sub)
    db.commit()
    return {"message": "删除成功"}
```

- [ ] **Step 4: Register router in main.py**

Add to imports:
```python
from .api import tracks
```

Add router registration (before the final block):
```python
app.include_router(tracks.router, prefix="/api", dependencies=[Depends(get_current_user)])
```

- [ ] **Step 5: Run tests**

```bash
cd ArticleGeneratorService && python -m pytest tests/test_api_tracks.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add ArticleGeneratorService/app/api/tracks.py ArticleGeneratorService/app/main.py ArticleGeneratorService/tests/test_api_tracks.py
git commit -m "feat: add track management API with CRUD and sub-track support"
```

---

## 3. Track Management Frontend

**Files:**
- Create: `ArticleGeneratorAdm/src/api/modules/tracks.ts`
- Create: `ArticleGeneratorAdm/src/views/TracksView.vue`
- Modify: `ArticleGeneratorAdm/src/router/index.ts`

### Task 3.1: Create tracks API module

- [ ] **Step 1: Write tracks.ts**

```typescript
/**
 * 赛道 API
 */
import { get, post, put, del, patch } from "@/api/client";
import type { Track, SubTrack } from "@/api/types";

export default {
  fetchTracks: () => get<Track[]>("/tracks"),

  createTrack: (data: {
    name: string;
    description?: string;
    keywords?: string;
    forbidden_keywords?: string;
  }) => post<Track>("/tracks", data),

  getTrack: (id: number) => get<Track>(`/tracks/${id}`),

  updateTrack: (id: number, data: {
    name?: string;
    description?: string;
    keywords?: string;
    forbidden_keywords?: string;
  }) => put<Track>(`/tracks/${id}`, data),

  toggleTrackStatus: (id: number, status: number) =>
    patch(`/tracks/${id}/status`, { status }),

  deleteTrack: (id: number) => del(`/tracks/${id}`),

  createSubTrack: (trackId: number, data: { name: string; description?: string }) =>
    post<SubTrack>(`/tracks/${trackId}/sub-tracks`, data),

  updateSubTrack: (id: number, data: { name: string; description?: string }) =>
    put<SubTrack>(`/tracks/sub-tracks/${id}`, data),

  deleteSubTrack: (id: number) => del(`/tracks/sub-tracks/${id}`),
};
```

- [ ] **Step 2: Add types to types.ts**

```typescript
// In ArticleGeneratorAdm/src/api/types.ts, add:
export interface Track {
  id: number;
  name: string;
  description?: string;
  keywords?: string;
  forbidden_keywords?: string;
  status: number;
  sub_tracks: SubTrack[];
  created_at: string;
  updated_at: string;
}

export interface SubTrack {
  id: number;
  track_id: number;
  name: string;
  description?: string;
  created_at: string;
}
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorAdm/src/api/modules/tracks.ts ArticleGeneratorAdm/src/api/types.ts
git commit -m "feat: add tracks API client module and types"
```

### Task 3.2: Create TracksView.vue

- [ ] **Step 1: Write TracksView.vue**

```vue
<template>
  <div class="tracks-view">
    <PageHeader title="赛道管理" subtitle="管理内容分类体系，配置一级和二级赛道" />

    <div class="toolbar">
      <el-input v-model="searchText" placeholder="搜索赛道..." style="width: 240px" clearable />
      <el-button type="primary" @click="openCreateDialog">+ 新增赛道</el-button>
    </div>

    <el-table :data="filteredTracks" v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="赛道名称" min-width="140">
        <template #default="{ row }">
          <span style="font-weight: 600;">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
            {{ row.status === 1 ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="openEditDialog(row)">编辑</el-button>
          <el-button size="small" text @click="toggleStatus(row)">
            {{ row.status === 1 ? '停用' : '启用' }}
          </el-button>
          <el-popconfirm title="删除赛道将同时删除所有二级赛道，确认？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button size="small" text type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
      <!-- Expand row for sub-tracks -->
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="sub-track-section">
            <div class="sub-track-header">
              <strong>二级赛道</strong>
              <el-button size="small" type="primary" @click="openSubTrackDialog(row)">+ 添加</el-button>
            </div>
            <div v-if="!row.sub_tracks?.length" style="color: #999; padding: 12px 0;">暂无二级赛道</div>
            <div v-for="sub in row.sub_tracks" :key="sub.id" class="sub-track-row">
              <span>{{ sub.name }}</span>
              <span v-if="sub.description" style="color: #999; margin-left: 8px;">— {{ sub.description }}</span>
              <span style="flex: 1;"></span>
              <el-button size="small" text @click="openSubTrackEdit(sub)">编辑</el-button>
              <el-popconfirm title="确认删除？" @confirm="handleDeleteSub(sub.id, row)">
                <template #reference>
                  <el-button size="small" text type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- Track Create/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="editingTrack ? '编辑赛道' : '新增赛道'" width="500px">
      <el-form :model="form" label-position="top">
        <el-form-item label="赛道名称" required>
          <el-input v-model="form.name" placeholder="如：AI科技" />
        </el-form-item>
        <el-form-item label="赛道描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="赛道简介..." />
        </el-form-item>
        <el-form-item label="热门关键词 (JSON数组)">
          <el-input v-model="form.keywords" placeholder='["AI", "ChatGPT", "大模型"]' />
        </el-form-item>
        <el-form-item label="禁用关键词 (JSON数组)">
          <el-input v-model="form.forbidden_keywords" placeholder='["赌博", "色情"]' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- SubTrack Dialog -->
    <el-dialog v-model="subDialogVisible" title="二级赛道" width="400px">
      <el-form :model="subForm" label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="subForm.name" placeholder="如：大模型" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="subForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="subDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import tracksApi from "@/api/modules/tracks";
import type { Track, SubTrack } from "@/api/types";
import PageHeader from "@/components/PageHeader.vue";

const tracks = ref<Track[]>([]);
const loading = ref(false);
const searchText = ref("");

const filteredTracks = computed(() => {
  if (!searchText.value) return tracks.value;
  const q = searchText.value.toLowerCase();
  return tracks.value.filter(t => t.name.toLowerCase().includes(q));
});

// Track dialog
const dialogVisible = ref(false);
const editingTrack = ref<Track | null>(null);
const form = ref({ name: "", description: "", keywords: "", forbidden_keywords: "" });

function openCreateDialog() {
  editingTrack.value = null;
  form.value = { name: "", description: "", keywords: "", forbidden_keywords: "" };
  dialogVisible.value = true;
}

function openEditDialog(row: Track) {
  editingTrack.value = row;
  form.value = {
    name: row.name,
    description: row.description || "",
    keywords: row.keywords || "",
    forbidden_keywords: row.forbidden_keywords || "",
  };
  dialogVisible.value = true;
}

async function handleSave() {
  if (!form.value.name.trim()) {
    ElMessage.warning("请输入赛道名称");
    return;
  }
  try {
    if (editingTrack.value) {
      await tracksApi.updateTrack(editingTrack.value.id, form.value);
      ElMessage.success("赛道已更新");
    } else {
      await tracksApi.createTrack(form.value);
      ElMessage.success("赛道已创建");
    }
    dialogVisible.value = false;
    await fetchTracks();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

async function toggleStatus(row: Track) {
  const newStatus = row.status === 1 ? 0 : 1;
  await tracksApi.toggleTrackStatus(row.id, newStatus);
  row.status = newStatus;
  ElMessage.success(newStatus === 1 ? "已启用" : "已停用");
}

async function handleDelete(id: number) {
  await tracksApi.deleteTrack(id);
  ElMessage.success("赛道已删除");
  await fetchTracks();
}

// SubTrack dialog
const subDialogVisible = ref(false);
const editingSubTrack = ref<SubTrack | null>(null);
const currentTrack = ref<Track | null>(null);
const subForm = ref({ name: "", description: "" });

function openSubTrackDialog(track: Track) {
  currentTrack.value = track;
  editingSubTrack.value = null;
  subForm.value = { name: "", description: "" };
  subDialogVisible.value = true;
}

function openSubTrackEdit(sub: SubTrack) {
  editingSubTrack.value = sub;
  subForm.value = { name: sub.name, description: sub.description || "" };
  subDialogVisible.value = true;
}

async function handleSubSave() {
  if (!subForm.value.name.trim()) {
    ElMessage.warning("请输入二级赛道名称");
    return;
  }
  try {
    if (editingSubTrack.value) {
      await tracksApi.updateSubTrack(editingSubTrack.value.id, subForm.value);
    } else if (currentTrack.value) {
      await tracksApi.createSubTrack(currentTrack.value.id, subForm.value);
    }
    ElMessage.success("保存成功");
    subDialogVisible.value = false;
    await fetchTracks();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  }
}

async function handleDeleteSub(subId: number, track: Track) {
  await tracksApi.deleteSubTrack(subId);
  ElMessage.success("二级赛道已删除");
  await fetchTracks();
}

async function fetchTracks() {
  loading.value = true;
  try {
    const { data } = await tracksApi.fetchTracks();
    tracks.value = data as any;
  } finally {
    loading.value = false;
  }
}

onMounted(fetchTracks);
</script>

<style scoped>
.tracks-view { max-width: 960px; margin: 0 auto; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.sub-track-section { padding: 8px 24px 16px; }
.sub-track-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.sub-track-row { display: flex; align-items: center; padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
</style>
```

- [ ] **Step 2: Add route to router/index.ts**

```typescript
{ path: "tracks", name: "Tracks", component: () => import("@/views/TracksView.vue"), meta: { title: "赛道管理" } },
```

- [ ] **Step 3: Start dev server and verify page loads**

```bash
cd ArticleGeneratorAdm && npm run dev
```
Navigate to http://localhost:5173/tracks — verify table loads, create/edit/delete operations work.

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorAdm/src/views/TracksView.vue ArticleGeneratorAdm/src/router/index.ts
git commit -m "feat: add track management page with CRUD and sub-track support"
```

---

## 4. MP Account Management Backend

**Files:**
- Modify: `ArticleGeneratorService/app/models.py` — add MpAccount
- Modify: `ArticleGeneratorService/app/schemas.py` — add MpAccount schemas
- Create: `ArticleGeneratorService/app/api/mp_accounts.py`
- Modify: `ArticleGeneratorService/app/main.py` — register router

### Task 4.1: Add MpAccount model and schemas

- [ ] **Step 1: Add model to models.py**

```python
class MpAccount(Base):
    """公众号"""
    __tablename__ = "mp_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    alias = Column(String(100))
    fakeid = Column(String(100))
    biz = Column(String(100))
    avatar = Column(String(500))
    description = Column(Text)
    track_ids = Column(Text)  # JSON string
    article_count = Column(Integer, default=0)
    last_collect_time = Column(DateTime)
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 2: Add schemas to schemas.py**

```python
# ----- 公众号 -----
class MpAccountBase(BaseModel):
    name: str
    alias: Optional[str] = None
    fakeid: Optional[str] = None
    biz: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    track_ids: Optional[str] = None

class MpAccountCreate(MpAccountBase): pass

class MpAccountUpdate(BaseModel):
    name: Optional[str] = None
    alias: Optional[str] = None
    fakeid: Optional[str] = None
    biz: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    track_ids: Optional[str] = None

class MpAccountResponse(MpAccountBase):
    id: int
    article_count: int = 0
    last_collect_time: Optional[datetime] = None
    status: int = 1
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

class MpAccountImportByName(BaseModel):
    names: List[str]
    credential_id: int

class MpAccountImportByUrl(BaseModel):
    urls: List[str]
    credential_id: int
```

- [ ] **Step 3: Verify models and schemas load**

```bash
cd ArticleGeneratorService && python -c "from app.models import MpAccount; from app.schemas import MpAccountCreate, MpAccountResponse; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/models.py ArticleGeneratorService/app/schemas.py
git commit -m "feat: add MpAccount model and schemas"
```

### Task 4.2: Create mp_accounts API module (CRUD first, import later)

- [ ] **Step 1: Write api/mp_accounts.py**

Following the same pattern as accounts.py but for mp_accounts:

```python
"""
公众号管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import MpAccount
from ..schemas import MpAccountCreate, MpAccountUpdate, MpAccountResponse
from ..deps import get_current_user

router = APIRouter(prefix="/mp-accounts", tags=["公众号管理"])


@router.get("", response_model=List[MpAccountResponse])
def list_mp_accounts(
    db: Session = Depends(get_db),
    track_id: Optional[int] = Query(None),
    status: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    """获取公众号列表"""
    q = db.query(MpAccount)
    if track_id is not None:
        q = q.filter(MpAccount.track_ids.contains(str(track_id)))
    if status is not None:
        q = q.filter(MpAccount.status == status)
    if search:
        q = q.filter(
            (MpAccount.name.contains(search)) | (MpAccount.alias.contains(search))
        )
    return q.order_by(MpAccount.id.desc()).all()


@router.post("", response_model=MpAccountResponse)
def create_mp_account(data: MpAccountCreate, db: Session = Depends(get_db)):
    """手动新增公众号"""
    account = MpAccount(**data.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=MpAccountResponse)
def get_mp_account(account_id: int, db: Session = Depends(get_db)):
    """获取公众号详情"""
    account = db.query(MpAccount).filter(MpAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="公众号不存在")
    return account


@router.put("/{account_id}", response_model=MpAccountResponse)
def update_mp_account(account_id: int, data: MpAccountUpdate, db: Session = Depends(get_db)):
    """编辑公众号"""
    account = db.query(MpAccount).filter(MpAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="公众号不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(account, k, v)
    db.commit()
    db.refresh(account)
    return account


@router.patch("/{account_id}/status")
def toggle_mp_account_status(account_id: int, data: dict, db: Session = Depends(get_db)):
    """启停公众号"""
    account = db.query(MpAccount).filter(MpAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="公众号不存在")
    account.status = data.get("status", account.status)
    db.commit()
    return {"message": "状态已更新"}


@router.delete("/{account_id}")
def delete_mp_account(account_id: int, db: Session = Depends(get_db)):
    """删除公众号"""
    account = db.query(MpAccount).filter(MpAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="公众号不存在")
    db.delete(account)
    db.commit()
    return {"message": "删除成功"}
```

- [ ] **Step 2: Register router in main.py**

```python
from .api import mp_accounts
# In router registration section:
app.include_router(mp_accounts.router, prefix="/api", dependencies=[Depends(get_current_user)])
```

- [ ] **Step 3: Write and run tests (following test_api_tracks.py pattern)**

Create `ArticleGeneratorService/tests/test_api_mp_accounts.py` with tests for list, create, update, toggle, delete.

```bash
cd ArticleGeneratorService && python -m pytest tests/test_api_mp_accounts.py -v
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/api/mp_accounts.py ArticleGeneratorService/app/main.py ArticleGeneratorService/tests/test_api_mp_accounts.py
git commit -m "feat: add MP account management API with CRUD and filtering"
```

### Task 4.3: Implement import endpoints (after collector MpClient exists)

Note: The import-by-name and import-by-url endpoints depend on MpClient (Task 10.2-10.3). Add these endpoints AFTER the collector engine is built.

**Add to mp_accounts.py:**

```python
from ..schemas import MpAccountImportByName, MpAccountImportByUrl

@router.post("/import-by-name")
def import_by_name(data: MpAccountImportByName, db: Session = Depends(get_db)):
    """通过公众号名称批量导入"""
    from ..collector.mp_client import MpClient
    # Load credential
    credential = db.query(MpCredential).filter(
        MpCredential.id == data.credential_id
    ).first()
    if not credential:
        raise HTTPException(status_code=404, detail="凭证不存在")
    if credential.status in ("expired", "error"):
        raise HTTPException(status_code=400, detail=f"凭证状态异常: {credential.status}")

    client = MpClient(credential.token, credential.cookie)
    results = {"success": [], "failed": []}
    for name in data.names:
        try:
            info = client.search_account(name.strip())
            if info:
                account = MpAccount(
                    name=info["name"], alias=info.get("alias"),
                    fakeid=info["fakeid"], biz=info.get("biz"),
                    avatar=info.get("avatar"), description=info.get("description"),
                )
                db.add(account)
                db.flush()
                results["success"].append({"name": name, "id": account.id})
            else:
                results["failed"].append({"name": name, "reason": "未找到"})
        except Exception as e:
            results["failed"].append({"name": name, "reason": str(e)})
    db.commit()
    return results


@router.post("/import-by-url")
def import_by_url(data: MpAccountImportByUrl, db: Session = Depends(get_db)):
    """通过文章链接批量导入"""
    import re
    from ..collector.mp_client import MpClient
    # Similar to name import but extract biz from URL and resolve account
    results = {"success": [], "failed": []}
    for url in data.urls:
        match = re.search(r'mp\.weixin\.qq\.com/s/([^?&]+)', url.strip())
        if not match:
            results["failed"].append({"url": url, "reason": "无法解析文章链接"})
            continue
        try:
            # Use MpClient to fetch account info from article page
            # Implementation depends on HTML parsing logic
            pass
        except Exception as e:
            results["failed"].append({"url": url, "reason": str(e)})
    return results
```

- [ ] **Commit**

```bash
git add ArticleGeneratorService/app/api/mp_accounts.py
git commit -m "feat: add MP account import-by-name and import-by-url endpoints"
```

---

## 5. MP Account Management Frontend

**Files:**
- Create: `ArticleGeneratorAdm/src/api/modules/mpAccounts.ts`
- Create: `ArticleGeneratorAdm/src/views/MpAccountsView.vue`
- Modify: `ArticleGeneratorAdm/src/router/index.ts`

### Task 5.1: Create mpAccounts API module and view

Following the exact same pattern as tracks.ts and TracksView.vue.

- [ ] **Step 1: Write mpAccounts.ts** (pattern identical to tracks.ts)

- [ ] **Step 2: Add MpAccount type to types.ts**

```typescript
export interface MpAccount {
  id: number;
  name: string;
  alias?: string;
  fakeid?: string;
  biz?: string;
  avatar?: string;
  description?: string;
  track_ids?: string;
  article_count: number;
  last_collect_time?: string;
  status: number;
  created_at: string;
  updated_at: string;
}
```

- [ ] **Step 3: Write MpAccountsView.vue**

Following TracksView pattern: table with track filter dropdown, status filter, search input. Import modal with two tabs (名称导入 + 链接导入). Each tab has a textarea + credential selector + submit button.

- [ ] **Step 4: Add route, start dev server, verify**

```bash
cd ArticleGeneratorAdm && npm run dev
```
Navigate to /mp-accounts — verify list, filters, CRUD, import modal.

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorAdm/src/api/modules/mpAccounts.ts ArticleGeneratorAdm/src/api/types.ts ArticleGeneratorAdm/src/views/MpAccountsView.vue ArticleGeneratorAdm/src/router/index.ts
git commit -m "feat: add MP account management page with import modal"
```

---

## 6. Collection Credential Backend & Frontend

Following the established patterns (models → schemas → API → frontend module → view).

### Task 6.1: Credential model + schemas + API

- [ ] **Step 1: Add MpCredential model to models.py**

```python
class MpCredential(Base):
    """采集凭证"""
    __tablename__ = "mp_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    token = Column(String(500), nullable=False)
    cookie = Column(Text, nullable=False)
    status = Column(String(20), default="normal")
    check_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: Add schemas to schemas.py**

```python
# ----- 采集凭证 -----
class MpCredentialCreate(BaseModel):
    name: str
    token: str
    cookie: str

class MpCredentialUpdate(BaseModel):
    name: Optional[str] = None
    token: Optional[str] = None
    cookie: Optional[str] = None

class MpCredentialResponse(BaseModel):
    id: int
    name: str
    token: str = Field(..., description="已掩码")
    cookie: str = Field(..., description="已掩码")
    status: str
    check_time: Optional[datetime] = None
    created_at: datetime
    class Config: from_attributes = True

    @field_validator("token", mode="after")
    @classmethod
    def mask_token(cls, v): return mask_api_key(v)

    @field_validator("cookie", mode="after")
    @classmethod
    def mask_cookie(cls, v):
        if not v or len(v) <= 20: return v
        return v[:10] + "***" + v[-10:]
```

- [ ] **Step 3: Create api/credentials.py** (CRUD + manual check endpoint)

The check endpoint uses a minimal searchbiz call (Task 10) to test credential validity.

- [ ] **Step 4: Register router, write tests, commit**

### Task 6.2: CredentialsView frontend

Following existing view patterns — card list showing credential name, status badge (colored), check_time. Add/edit modal with name, token, cookie fields. "检测" button triggers manual health check.

- [ ] **Write CredentialsView.vue, add route, verify, commit**

---

## 7. Collection Task Management Backend & Frontend

### Task 7.1: Task model + schemas + API

- [ ] **Add CollectTask model, schemas, api/collect_tasks.py** (CRUD + execute/pause/resume)

### Task 7.2: CollectTasksView frontend

- [ ] **Multi-level selector component**

Custom component: track checkbox list → expand → account checkboxes inside. When a track is checked, all its accounts are checked by default. Users can uncheck individual accounts.

```vue
<!-- Key template structure for multi-level selector -->
<div v-for="track in tracksWithAccounts" :key="track.id" class="track-group">
  <el-checkbox v-model="track.checked" @change="onTrackToggle(track)">
    {{ track.name }} ({{ track.accounts.length }}个公众号)
  </el-checkbox>
  <div v-if="track.checked" class="account-list" style="margin-left: 28px;">
    <el-checkbox
      v-for="acc in track.accounts"
      :key="acc.id"
      v-model="acc.checked"
      @change="onAccountToggle"
    >
      {{ acc.name }}
    </el-checkbox>
  </div>
</div>
```

- [ ] **Collect mode + schedule type form controls**
- [ ] **Write CollectTasksView.vue, add route, verify, commit**

---

## 8. Collection Engine (MpClient)

**Files:**
- Create: `ArticleGeneratorService/app/collector/__init__.py`
- Create: `ArticleGeneratorService/app/collector/mp_client.py`

### Task 8.1: Implement MpClient

- [ ] **Step 1: Write mp_client.py**

```python
"""
微信公众号 API 客户端
封装 searchbiz、appmsg 接口调用和文章 HTML 获取
"""
import time
import random
import hashlib
import re
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime


class RateLimiter:
    """请求频率控制器 — 防风控"""

    def __init__(self, min_interval: float = 15.0, jitter: float = 5.0):
        self.min_interval = min_interval
        self.jitter = jitter
        self._last_request = 0.0

    def wait(self):
        """等待直到满足最小间隔"""
        elapsed = time.monotonic() - self._last_request
        wait_time = self.min_interval + random.uniform(0, self.jitter)
        if elapsed < wait_time:
            time.sleep(wait_time - elapsed)
        self._last_request = time.monotonic()


class MpClient:
    """微信公众号客户端"""

    BASE_URL = "https://mp.weixin.qq.com"

    def __init__(self, token: str, cookie: str, min_interval: float = 15.0):
        self.token = token
        self.cookie = cookie
        self.limiter = RateLimiter(min_interval=min_interval)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Cookie": cookie,
            "Referer": f"{self.BASE_URL}/cgi-bin/appmsg",
        })

    def _get(self, path: str, params: dict) -> requests.Response:
        """带频率控制的 GET 请求"""
        self.limiter.wait()
        url = f"{self.BASE_URL}{path}"
        params["token"] = self.token
        params["lang"] = "zh_CN"
        params["f"] = "json"
        return self.session.get(url, params=params, timeout=30)

    def search_account(self, name: str) -> Optional[Dict[str, Any]]:
        """搜索公众号: GET /cgi-bin/searchbiz → 返回 fakeid, biz, avatar, description"""
        resp = self._get("/cgi-bin/searchbiz", {
            "action": "search_biz",
            "query": name,
            "begin": "0",
            "count": "1",
        })
        data = resp.json()
        biz_list = data.get("list", [])
        if not biz_list:
            return None
        item = biz_list[0]
        return {
            "name": item.get("nickname", name),
            "alias": item.get("alias", ""),
            "fakeid": str(item.get("fakeid", "")),
            "biz": item.get("alias", ""),
            "avatar": item.get("round_head_img", ""),
            "description": item.get("signature", ""),
        }

    def fetch_article_list(
        self, fakeid: str, mode: str = "incremental",
        date_start: Optional[str] = None, date_end: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取文章列表: GET /cgi-bin/appmsg

        Returns list of {title, link, aid, create_time, cover}
        """
        articles = []
        count = self._mode_count(mode)
        begin = 0

        while begin < count:
            params = {
                "action": "list_ex",
                "type": "9",
                "query": "",
                "fakeid": fakeid,
                "begin": str(begin),
                "count": "10",
            }
            resp = self._get("/cgi-bin/appmsg", params)
            data = resp.json()

            app_msg_list = data.get("app_msg_list", [])
            if not app_msg_list:
                break

            for msg in app_msg_list:
                articles.append({
                    "title": msg.get("title", ""),
                    "link": msg.get("link", ""),
                    "aid": str(msg.get("aid", "")),
                    "create_time": msg.get("create_time", 0),
                    "cover": msg.get("cover", ""),
                    "digest": msg.get("digest", ""),
                })

            if len(app_msg_list) < 10:
                break  # No more pages
            begin += 10

        return articles

    def fetch_article_html(self, url: str) -> str:
        """获取文章原始 HTML"""
        self.limiter.wait()
        resp = self.session.get(url, timeout=30)
        resp.encoding = "utf-8"
        return resp.text

    def extract_metadata(self, html: str) -> Dict[str, Any]:
        """从 HTML 提取元数据: title, author, published_at"""
        result = {"title": "", "author": "", "published_at": None}

        title_match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
        if title_match:
            result["title"] = title_match.group(1)

        author_match = re.search(r'<meta[^>]+property="og:article:author"[^>]+content="([^"]+)"', html)
        if author_match:
            result["author"] = author_match.group(1)

        time_match = re.search(r'<meta[^>]+property="og:article:publish_time"[^>]+content="([^"]+)"', html)
        if time_match:
            result["published_at"] = datetime.fromtimestamp(int(time_match.group(1)))

        return result

    @staticmethod
    def content_hash(html: str) -> str:
        return hashlib.sha256(html.encode("utf-8")).hexdigest()

    @staticmethod
    def estimate_word_count(html: str) -> int:
        """粗略估算字数"""
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\s+', '', text)
        return len(text)

    @staticmethod
    def _mode_count(mode: str) -> int:
        """解析采集模式对应的文章数量"""
        mode_map = {
            "history_50": 50, "history_100": 100, "history_200": 200,
            "incremental": 10,
        }
        return mode_map.get(mode, 10)

    def check_health(self) -> bool:
        """凭证有效性检测 — 用已知公众号名尝试搜索"""
        try:
            resp = self._get("/cgi-bin/searchbiz", {
                "action": "search_biz",
                "query": "人民日报",
                "begin": "0",
                "count": "1",
            })
            data = resp.json()
            return data.get("base_resp", {}).get("ret") == 0
        except Exception:
            return False
```

- [ ] **Step 2: Write unit test for MpClient**

```python
# ArticleGeneratorService/tests/test_mp_client.py
import pytest
from unittest.mock import patch, MagicMock
from app.collector.mp_client import MpClient, RateLimiter

def test_rate_limiter_waits():
    limiter = RateLimiter(min_interval=0.1, jitter=0.0)
    start = __import__("time").monotonic()
    limiter.wait()
    limiter.wait()
    elapsed = __import__("time").monotonic() - start
    assert elapsed >= 0.1

def test_mode_count():
    assert MpClient._mode_count("history_50") == 50
    assert MpClient._mode_count("incremental") == 10

def test_content_hash():
    html = "<html><body>test</body></html>"
    h = MpClient.content_hash(html)
    assert len(h) == 64
    assert MpClient.content_hash(html) == h  # Deterministic

@patch("app.collector.mp_client.requests.Session")
def test_search_account_found(mock_session):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "list": [{
            "nickname": "36氪", "alias": "wow36kr",
            "fakeid": "12345", "round_head_img": "http://img",
            "signature": "科技商业媒体"
        }]
    }
    mock_session.return_value.get.return_value = mock_resp

    client = MpClient("test_token", "test_cookie")
    result = client.search_account("36氪")
    assert result["name"] == "36氪"
    assert result["fakeid"] == "12345"

@patch("app.collector.mp_client.requests.Session")
def test_search_account_not_found(mock_session):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"list": []}
    mock_session.return_value.get.return_value = mock_resp

    client = MpClient("test_token", "test_cookie")
    result = client.search_account("不存在")
    assert result is None

def test_extract_metadata():
    html = '''
    <meta property="og:title" content="Test Title"/>
    <meta property="og:article:author" content="Test Author"/>
    '''
    client = MpClient("t", "c")
    meta = client.extract_metadata(html)
    assert meta["title"] == "Test Title"
    assert meta["author"] == "Test Author"
```

- [ ] **Step 3: Run tests**

```bash
cd ArticleGeneratorService && python -m pytest tests/test_mp_client.py -v
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/collector/ ArticleGeneratorService/tests/test_mp_client.py
git commit -m "feat: add MpClient with searchbiz/appmsg support, rate limiter, health check"
```

---

## 9. Collection Engine (Worker & Scheduler)

**Files:**
- Create: `ArticleGeneratorService/app/collector/worker.py`
- Modify: `ArticleGeneratorService/app/tasks.py` — register collector tasks
- Modify: Celery Beat config

### Task 9.1: Implement collector worker

- [ ] **Step 1: Write worker.py**

```python
"""
采集引擎 Worker — Celery 任务
"""
import json
import logging
from datetime import datetime, timezone
from celery import shared_task
from ..database import SessionLocal
from ..models import MpCredential, MpAccount, CollectTask, MpMaterial, CollectLog
from .mp_client import MpClient

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


@shared_task(bind=True, max_retries=0)
def execute_collect_task(self, task_id: int):
    """执行采集任务"""
    db = SessionLocal()
    task = None
    log_entry = None
    try:
        task = db.query(CollectTask).filter(CollectTask.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        # 1. Credential pre-check
        credential = db.query(MpCredential).filter(
            MpCredential.id == task.credential_id
        ).first()
        if not credential:
            _fail_task(db, task, "凭证不存在")
            return
        if credential.status in ("expired", "error"):
            _fail_task(db, task, f"凭证状态异常: {credential.status}")
            return

        # 2. Resolve target accounts
        accounts = _resolve_accounts(db, task)
        if not accounts:
            _fail_task(db, task, "没有匹配的公众号")
            return

        # 3. Update task status
        task.status = "running"
        db.commit()

        client = MpClient(credential.token, credential.cookie)

        # 4. Collect from each account
        for account in accounts:
            log_entry = _create_log(db, task.id, account.id)
            try:
                _collect_from_account(db, client, account, task)
            except Exception as e:
                logger.exception(f"Collection failed for {account.name}")
                _update_log(db, log_entry, error=str(e))
            finally:
                _update_account_stats(db, account.id)

        # 5. Mark task complete
        task.status = "idle"
        db.commit()

    except Exception as e:
        logger.exception(f"Task {task_id} failed")
        if task:
            task.status = "error"
            db.commit()
    finally:
        db.close()


def _resolve_accounts(db, task: CollectTask):
    """解析目标公众号列表"""
    account_ids = None
    if task.account_ids:
        try:
            account_ids = json.loads(task.account_ids)
        except (json.JSONDecodeError, TypeError):
            pass

    if account_ids:
        return db.query(MpAccount).filter(
            MpAccount.id.in_(account_ids),
            MpAccount.status == 1,
        ).all()

    # By track_ids
    track_ids = None
    if task.track_ids:
        try:
            track_ids = json.loads(task.track_ids)
        except (json.JSONDecodeError, TypeError):
            pass

    if track_ids:
        accounts = []
        all_active = db.query(MpAccount).filter(MpAccount.status == 1).all()
        for acc in all_active:
            if acc.track_ids:
                try:
                    acc_tracks = json.loads(acc.track_ids)
                except (json.JSONDecodeError, TypeError):
                    continue
                if any(str(t) in [str(tt) for tt in track_ids] for t in acc_tracks):
                    accounts.append(acc)
        return accounts

    return db.query(MpAccount).filter(MpAccount.status == 1).all()


def _collect_from_account(db, client: MpClient, account: MpAccount, task: CollectTask):
    """从单个公众号采集文章"""
    if not account.fakeid:
        # Try to get fakeid first
        info = client.search_account(account.name)
        if info:
            account.fakeid = info["fakeid"]
            account.biz = info.get("biz")
            account.avatar = info.get("avatar")
            account.description = account.description or info.get("description")
            db.commit()

    if not account.fakeid:
        logger.warning(f"Cannot collect from {account.name}: no fakeid")
        return

    # Fetch article list
    articles = client.fetch_article_list(
        account.fakeid, task.collect_mode,
        date_start=task.date_start.isoformat() if task.date_start else None,
        date_end=task.date_end.isoformat() if task.date_end else None,
    )

    success = 0
    fail = 0
    for art in articles:
        try:
            # URL dedup
            existing = db.query(MpMaterial).filter(
                MpMaterial.original_url == art["link"]
            ).first()
            if existing:
                continue

            # Fetch HTML
            html = client.fetch_article_html(art["link"])
            content_hash = MpClient.content_hash(html)

            # Content hash dedup
            hash_exists = db.query(MpMaterial).filter(
                MpMaterial.content_hash == content_hash
            ).first()
            if hash_exists:
                continue

            meta = client.extract_metadata(html)
            word_count = MpClient.estimate_word_count(html)

            material = MpMaterial(
                account_id=account.id,
                title=art["title"] or meta["title"],
                author=meta["author"],
                original_url=art["link"],
                cover_url=art["cover"],
                summary=art.get("digest", ""),
                raw_html=html,
                content_hash=content_hash,
                word_count=word_count,
                published_at=meta["published_at"],
                collected_at=_utcnow(),
            )
            db.add(material)
            success += 1
        except Exception as e:
            logger.exception(f"Failed to collect article: {art.get('link')}")
            fail += 1

    db.commit()
    logger.info(f"Collected from {account.name}: {success} success, {fail} failed")


def _create_log(db, task_id: int, account_id: int) -> CollectLog:
    log = CollectLog(
        task_id=task_id, account_id=account_id,
        start_time=_utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _update_log(db, log: CollectLog, error: str = None, **counts):
    log.end_time = _utcnow()
    for k, v in counts.items():
        setattr(log, k, v)
    if error:
        log.error_message = error
    db.commit()


def _update_account_stats(db, account_id: int):
    account = db.query(MpAccount).filter(MpAccount.id == account_id).first()
    if account:
        account.last_collect_time = _utcnow()
        count = db.query(MpMaterial).filter(
            MpMaterial.account_id == account_id
        ).count()
        account.article_count = count
        db.commit()


def _fail_task(db, task: CollectTask, reason: str):
    task.status = "error"
    db.commit()
    logger.error(f"Task {task.id} failed: {reason}")
```

- [ ] **Step 2: Register task in tasks.py**

```python
# In ArticleGeneratorService/app/tasks.py, add:
from app.collector.worker import execute_collect_task, check_credentials_health
```

- [ ] **Step 3: Write scheduler (Celery Beat)**

```python
# ArticleGeneratorService/app/collector/scheduler.py
"""
Celery Beat 调度配置
在 celery config 中添加:
  beat_schedule = {
      'check-credentials-health': {
          'task': 'app.collector.worker.check_credentials_health',
          'schedule': crontab(hour='*/6'),
      },
  }

对于 cron/interval 类型的 collect_tasks，由 Celery Beat 动态扫描或
在每个 Beat tick 时检查是否有到期任务。
"""
```

- [ ] **Step 4: Write tests for worker (mock MpClient)**

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorService/app/collector/worker.py ArticleGeneratorService/app/collector/scheduler.py ArticleGeneratorService/app/tasks.py
git commit -m "feat: add collector worker with dedup, rate limiting, and logging"
```

---

## 10. Materials Backend & Frontend

**Files:**
- Create: `ArticleGeneratorService/app/api/materials.py`
- Create: `ArticleGeneratorService/app/api/collect_logs.py`
- Create: `ArticleGeneratorAdm/src/api/modules/materials.ts`
- Create: `ArticleGeneratorAdm/src/views/MaterialsView.vue`

### Task 10.1: Materials API

Following the pattern from articles.py — list with filters, detail with lazy parse.

```python
# Key endpoint: POST /api/materials/{id}/parse
@router.post("/{material_id}/parse")
def parse_material(material_id: int, db: Session = Depends(get_db)):
    """触发延迟解析: HTML → Markdown"""
    material = db.query(MpMaterial).filter(MpMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    if material.content_markdown:
        return {"content_markdown": material.content_markdown, "cached": True}

    # Use Turndown library (pip install turndown) or regex-based conversion
    from markdownify import markdownify
    md = markdownify(material.raw_html or "", heading_style="ATX")
    material.content_markdown = md
    db.commit()
    return {"content_markdown": md, "cached": False}
```

### Task 10.2: MaterialsView frontend

Following existing view patterns but with:
- Multi-filter bar (track, account, date range, search)
- Detail modal/drawer with HTML/Markdown tab switching
- Lazy parse on tab switch
- "创作方向" button placeholder

---

## 11. Integration & Verification

### Task 11.1: End-to-end integration test

- [ ] **Step 1: Start backend with fresh dev DB**

```bash
cd ArticleGeneratorService && python -m app.main
```
Verify /docs shows all new API endpoints.

- [ ] **Step 2: Start frontend dev server**

```bash
cd ArticleGeneratorAdm && npm run dev
```

- [ ] **Step 3: Full flow manual test**

1. Login → navigate to /tracks → create "AI科技" track
2. Navigate to /credentials → add a test credential
3. Navigate to /mp-accounts → add "36氪" account, assign to "AI科技" track
4. Navigate to /collect-tasks → create task (track=AI科技, mode=incremental, manual)
5. Execute task → verify /materials shows collected articles
6. Click material → verify HTML tab → switch to Markdown tab → verify parse

- [ ] **Step 4: Verify sidebar navigation**

All new routes visible: 赛道管理, 公众号管理, 采集凭证, 采集任务, 素材中心

---

## Summary

**Total tasks:** 11 groups, ~63 individual steps
**Estimated time:** 12-18 days for complete Phase 1 MVP
**Dependencies:** Must follow order within each group; groups 1→2→3→4+5→6+7→8+9→10→11
