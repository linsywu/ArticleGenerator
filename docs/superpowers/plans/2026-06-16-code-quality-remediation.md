# 代码质量修正 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对 ArticleGenerator 全栈执行 27 项代码质量修正（P0 安全→P1 架构→P2 一致性→P3 优化）

**Architecture:** P0 建立 JWT 鉴权基础 + 脱敏 + 统一 Engine + 死代码清理 + CORS → P1 抽取 Service 层 + 异步化 + 文件拆分 + 前端重构 → P2 测试补全 + DB 迁移 + 日志 + 常量集中 → P3 文档统一 + 布局优化 + CRUD 抽象

**Tech Stack:** FastAPI + SQLAlchemy + Celery + python-jose + passlib (后端), Vue 3 + Element Plus + Vite + Pinia (前端)

**Specs:** `openspec/changes/code-quality-remediation/specs/` (24 capability specs)
**Design:** `openspec/changes/code-quality-remediation/design.md`

---

## 1. P0 — 安全与正确性

### Task 1.1: T01 — JWT 鉴权基础框架

**Spec:** `openspec/changes/code-quality-remediation/specs/user-auth/spec.md`
**Files:**
- Create: `ArticleGeneratorService/app/auth.py`
- Create: `ArticleGeneratorService/app/deps.py`
- Create: `ArticleGeneratorService/app/api/auth.py`
- Modify: `ArticleGeneratorService/app/models.py` (append User model)
- Modify: `ArticleGeneratorService/app/main.py` (register auth router, global Depends)
- Modify: `ArticleGeneratorService/app/config.py` (add JWT/env config)
- Modify: `ArticleGeneratorService/.env.example`
- Create: `ArticleGeneratorAdm/src/views/LoginView.vue`
- Modify: `ArticleGeneratorAdm/src/router/index.ts` (add /login + beforeEach guard)
- Modify: `ArticleGeneratorAdm/src/api/client.ts` (add JWT interceptor)

**Dependencies:** `python-jose[cryptography]`, `passlib[bcrypt]`

- [ ] **Step 1: Install dependencies**

```bash
cd ArticleGeneratorService && pip install "python-jose[cryptography]" passlib[bcrypt]
```

- [ ] **Step 2: Add JWT config to config.py**

Append to `ArticleGeneratorService/app/config.py`:

```python
# JWT 鉴权
jwt_secret: str = "dev-secret-change-in-production"
access_token_expire_minutes: int = 1440  # 24h

# 种子管理员
seed_username: str = "admin"
seed_password: str = "admin123"
```

- [ ] **Step 3: Create app/auth.py**

Create `ArticleGeneratorService/app/auth.py`:

```python
"""JWT 签发与验证"""
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
```

- [ ] **Step 4: Create app/deps.py**

Create `ArticleGeneratorService/app/deps.py`:

```python
"""FastAPI 依赖注入"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .auth import decode_access_token
from .database import get_db
from .models import User

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """从 Bearer token 解析当前用户"""
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效或过期的 token")
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 token payload")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user
```

- [ ] **Step 5: Add User model to models.py**

Append to `ArticleGeneratorService/app/models.py`:

```python
class User(Base):
    """用户（鉴权）"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(200), nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
```

- [ ] **Step 6: Create POST /api/auth/login endpoint**

Create `ArticleGeneratorService/app/api/auth.py`:

```python
"""鉴权 API"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models import User
from ..auth import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["鉴权"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token(data={"sub": user.username})
    return LoginResponse(access_token=token)
```

- [ ] **Step 7: Update main.py — register auth router + seed user + protect routes**

Replace `ArticleGeneratorService/app/main.py`:

```python
"""
ArticleGenerator 后端主入口
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db, SessionLocal
from .auth import get_password_hash
from .models import User  # noqa: ensure model is imported
from .deps import get_current_user
from .api import accounts, hotspot_sources, hotspots, articles, generate, providers, scenario_configs, reference_articles, distill, generation_logs, tasks, auth

app = FastAPI(
    title="ArticleGenerator API",
    description="半自动化内容创作辅助系统",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if "," in settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 公开路由（无需鉴权）
app.include_router(auth.router, prefix="/api")

# 受保护路由
app.include_router(accounts.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(hotspot_sources.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(hotspots.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(articles.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(generate.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(providers.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(scenario_configs.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(reference_articles.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(distill.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(generation_logs.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(tasks.router, prefix="/api", dependencies=[Depends(get_current_user)])


@app.on_event("startup")
def startup():
    init_db()
    # 种子管理员用户
    db = SessionLocal()
    try:
        if not db.query(User).first():
            from .config import settings
            db.add(User(
                username=settings.seed_username,
                password_hash=get_password_hash(settings.seed_password),
            ))
            db.commit()
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "ArticleGenerator API", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Update .env.example**

Replace `ArticleGeneratorService/.env.example`:

```bash
# 数据库
DATABASE_URL=sqlite:///./article_generator.db

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM 服务
LLM_SERVICE_URL=http://localhost:8001

# JWT 鉴权
JWT_SECRET=change-me-to-a-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440
SEED_USERNAME=admin
SEED_PASSWORD=change-me

# CORS（开发用 localhost:5173，生产用实际域名）
CORS_ORIGINS=http://localhost:5173
```

- [ ] **Step 9: Create frontend LoginView.vue**

Create `ArticleGeneratorAdm/src/views/LoginView.vue`:

```vue
<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2>墨斋 · 登录</h2>
      <el-form ref="formRef" :model="form" label-width="0" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="handleLogin" style="width: 100%">登录</el-button>
        </el-form-item>
      </el-form>
      <p v-if="error" class="error-msg">{{ error }}</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";

const router = useRouter();
const loading = ref(false);
const error = ref("");
const form = reactive({ username: "", password: "" });

async function handleLogin() {
  if (!form.username || !form.password) {
    error.value = "请输入用户名和密码";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const res = await axios.post("/api/auth/login", form);
    localStorage.setItem("token", res.data.access_token);
    router.push("/");
  } catch (e: any) {
    error.value = e?.response?.data?.detail || "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; background: var(--ink-bg);
}
.login-card { width: 400px; }
.login-card h2 { text-align: center; margin-bottom: 24px; color: var(--text-primary); }
.error-msg { color: var(--el-color-danger); text-align: center; margin-top: -8px; }
</style>
```

- [ ] **Step 10: Update frontend router with auth guard**

Replace `ArticleGeneratorAdm/src/router/index.ts`:

```typescript
import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

export const routes: RouteRecordRaw[] = [
  { path: "/login", name: "Login", component: () => import("@/views/LoginView.vue"), meta: { title: "登录" } },
  { path: "/", redirect: "/create" },
  { path: "/create", name: "Create", component: () => import("@/views/CreateView.vue"), meta: { title: "文章创作" } },
  { path: "/review", name: "Review", component: () => import("@/views/ReviewView.vue"), meta: { title: "评审队列" } },
  { path: "/publish", name: "Publish", component: () => import("@/views/PublishView.vue"), meta: { title: "文章发布" } },
  { path: "/accounts", name: "Accounts", component: () => import("@/views/AccountsView.vue"), meta: { title: "账号风格" } },
  { path: "/inspiration", name: "Inspiration", component: () => import("@/views/HotspotsView.vue"), meta: { title: "灵感墙" } },
  { path: "/tasks", name: "Tasks", component: () => import("@/views/TasksView.vue"), meta: { title: "任务记录" } },
  { path: "/hotspot-sources", name: "HotspotSources", component: () => import("@/views/HotspotSourcesView.vue"), meta: { title: "热点源管理" } },
  { path: "/providers", name: "Providers", component: () => import("@/views/ProvidersView.vue"), meta: { title: "API供应商" } },
  { path: "/scenario-configs", name: "ScenarioConfigs", component: () => import("@/views/ScenarioConfigsView.vue"), meta: { title: "场景配置" } },
  { path: "/tasks-center", name: "TaskCenter", component: () => import("@/views/TaskCenterView.vue"), meta: { title: "任务中心" } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem("token");
  if (to.path !== "/login" && !token) {
    next("/login");
  } else if (to.path === "/login" && token) {
    next("/");
  } else {
    next();
  }
});

export default router;
```

- [ ] **Step 11: Update api/client.ts — add JWT interceptor**

In `ArticleGeneratorAdm/src/api/client.ts`, modify the axios instance creation and add request/response interceptors:

Replace the axios instance setup in client.ts:

```typescript
import axios from "axios";
import { ElMessage } from "element-plus";
import router from "@/router";

const client = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

// 请求拦截器：自动带 Authorization
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：401 → 清 token → 跳登录
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      router.push("/login");
    }
    ElMessage.error(error.response?.data?.detail || "请求失败");
    return Promise.reject(error);
  }
);

export default client;
```

Note: The existing `api` export object at the bottom of client.ts should be updated to use the new `client` instance. Adjust the `api` object's methods to use `client.get/post/put/delete` instead of the current raw axios calls.

- [ ] **Step 12: Verify — backend tests pass**

```bash
cd ArticleGeneratorService && python -c "
from app.auth import create_access_token, decode_access_token, get_password_hash, verify_password
# Test password hashing
h = get_password_hash('test123')
assert verify_password('test123', h)
assert not verify_password('wrong', h)
# Test JWT
token = create_access_token({'sub': 'admin'})
payload = decode_access_token(token)
assert payload['sub'] == 'admin'
# Test expired token
from datetime import timedelta
expired_token = create_access_token({'sub': 'admin'}, expires_delta=timedelta(seconds=-1))
assert decode_access_token(expired_token) is None
print('Auth unit tests: PASS')
"
```

- [ ] **Step 13: Verify — backend starts and /api/health is public**

```bash
cd ArticleGeneratorService && timeout 5 uvicorn app.main:app --host 127.0.0.1 --port 8000 2>&1 || true
# Test: GET /api/health returns 200 (no auth)
curl -s http://127.0.0.1:8000/api/health
# Test: GET /api/accounts returns 401 (no token)
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/accounts
# Expected: 401
```

- [ ] **Step 14: Verify — login works and protected endpoint accessible**

```bash
# Login
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
# Test protected endpoint
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/accounts -H "Authorization: Bearer $TOKEN"
# Expected: 200 (如果账号表为空) 或正常返回
```

- [ ] **Step 15: Commit**

```bash
git add ArticleGeneratorService/app/auth.py ArticleGeneratorService/app/deps.py \
        ArticleGeneratorService/app/api/auth.py ArticleGeneratorService/app/models.py \
        ArticleGeneratorService/app/main.py ArticleGeneratorService/app/config.py \
        ArticleGeneratorService/.env.example \
        ArticleGeneratorAdm/src/views/LoginView.vue \
        ArticleGeneratorAdm/src/router/index.ts \
        ArticleGeneratorAdm/src/api/client.ts
git commit -m "feat(T01): JWT 鉴权基础框架 — 登录/User模型/router守卫"
```

---

### Task 1.2: T02 — Provider api_key 脱敏

**Spec:** `openspec/changes/code-quality-remediation/specs/provider-api-key-security/spec.md`
**Files:**
- Modify: `ArticleGeneratorService/app/schemas.py`
- Modify: `ArticleGeneratorService/app/api/providers.py`

- [ ] **Step 1: Add mask function + masked provider response to schemas.py**

Add at module level in `schemas.py`:

```python
def mask_api_key(key: str) -> str:
    """掩码 api_key，如 sk-abc123...def → sk-a***def"""
    if not key or len(key) <= 7:
        return key
    return key[:3] + "***" + key[-4:]
```

Modify `ProviderResponse` to auto-mask:

```python
class ProviderResponse(ProviderBase):
    id: int
    enabled: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("api_key", mode="before")
    @classmethod
    def mask_key(cls, v: str) -> str:
        return mask_api_key(v)

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Update ProviderUpdate to allow empty key = keep existing**

In providers API (`providers.py`), modify the update endpoint:

```python
@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(provider_id: int, data: ProviderUpdate, db: Session = Depends(get_db)):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    update_data = data.model_dump(exclude_unset=True)
    # 如果 api_key 为空或未提供，保留原值
    if "api_key" in update_data and not update_data["api_key"]:
        del update_data["api_key"]
    for key, value in update_data.items():
        setattr(provider, key, value)
    db.commit()
    db.refresh(provider)
    return provider
```

- [ ] **Step 3: Verify — GET providers returns masked key**

```bash
# Restart backend, then:
curl -s http://127.0.0.1:8000/api/providers -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for p in data:
    key = p.get('api_key', '')
    assert '***' in key or len(key) <= 7, f'Key not masked: {key}'
print('Provider key masking: PASS')
"
```

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/schemas.py ArticleGeneratorService/app/api/providers.py
git commit -m "feat(T02): Provider api_key 响应掩码 + 留空不修改"
```

---

### Task 1.3: T03 — 统一数据库 Engine

**Spec:** `openspec/changes/code-quality-remediation/specs/unified-database-engine/spec.md`
**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py` (remove create_engine, import from database)
- Modify: `ArticleGeneratorService/app/database.py` (ensure absolute path for SQLite)
- Modify: `ArticleGeneratorService/app/config.py` (if needed)

- [ ] **Step 1: Remove duplicate engine from tasks.py**

In `tasks.py`, replace lines 10 and 36-37 (the `from sqlalchemy import create_engine` and engine/SessionLocal creation):

```python
# REMOVE:
# from sqlalchemy import create_engine
# engine = create_engine(settings.database_url, ...)
# SessionLocal = sessionmaker(bind=engine)

# REPLACE WITH:
from .database import SessionLocal
```

Also remove the `from sqlalchemy import create_engine` import if it exists on line 10.

- [ ] **Step 2: Ensure SQLite uses absolute path in database.py**

Modify `database.py`:

```python
from pathlib import Path
from .config import settings

connect_args = {}
db_url = settings.database_url
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # 确保相对路径转为绝对路径
    prefix = "sqlite:///"
    path = db_url[len(prefix):]
    if not Path(path).is_absolute():
        abs_path = str(Path.cwd() / path)
        db_url = prefix + abs_path

engine = create_engine(db_url, connect_args=connect_args, echo=False)
```

- [ ] **Step 3: Verify — Celery worker uses shared engine**

```bash
cd ArticleGeneratorService && python3 -c "
from app.tasks import SessionLocal
from app.database import SessionLocal as DSL
import inspect
# Verify SessionLocal in tasks.py comes from database.py
assert inspect.getfile(SessionLocal) == inspect.getfile(DSL), 'Different SessionLocal sources!'
print('Unified engine: PASS')
"
```

- [ ] **Step 4: Verify — pytest still passes**

```bash
cd ArticleGeneratorService && pytest tests/ -v
```

- [ ] **Step 5: Commit**

---

### Task 1.4: T04 — 修复 CreateView 步骤 6 死代码

**Spec:** `openspec/changes/code-quality-remediation/specs/frontend-dead-code-cleanup/spec.md`
**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CreateView.vue`

- [ ] **Step 1: Read and remove step 6 template**

In `CreateView.vue`, delete lines 162-177 (the `<div v-else key="step6">` block). Update the step indicator to show 5 steps max instead of 6.

Delete `submitForReview` function (around line 310).

Remove unreferenced reactive state variables used only by step 6.

- [ ] **Step 2: Verify — npm run build succeeds**

```bash
cd ArticleGeneratorAdm && npm run build
```

- [ ] **Step 3: Commit**

---

### Task 1.5: T05 — 清理孤儿页面

**Spec:** `openspec/changes/code-quality-remediation/specs/frontend-dead-code-cleanup/spec.md`

- [ ] **Step 1: Delete orphan view files**

```bash
rm ArticleGeneratorAdm/src/views/GenerateView.vue
rm ArticleGeneratorAdm/src/views/DistillView.vue
```

- [ ] **Step 2: Verify no residual references**

```bash
cd ArticleGeneratorAdm && grep -r "GenerateView\|DistillView" src/ --include="*.ts" --include="*.vue"
# Expected: no output
```

- [ ] **Step 3: Verify build succeeds**

```bash
cd ArticleGeneratorAdm && npm run build
```

- [ ] **Step 4: Commit**

---

### Task 1.6: T06 — 修复 CORS 配置

**Spec:** `openspec/changes/code-quality-remediation/specs/cors-configuration/spec.md`

- [ ] **Step 1: Fix CORS in main.py**

Modify the CORSMiddleware setup in `main.py`:

```python
# 解析 CORS origins
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if not origins:
    origins = ["http://localhost:5173"]  # 默认值

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=bool(origins),  # 仅具体 origin 时允许 credentials
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 2: Update .env.example CORS entry**

```bash
CORS_ORIGINS=http://localhost:5173
```

- [ ] **Step 3: Verify no ["*"] + credentials=True combination**

```bash
cd ArticleGeneratorService && python3 -c "
from app.config import settings
origins = [o.strip() for o in settings.cors_origins.split(',')]
assert '*' not in origins or not bool(origins), 'Wildcard + credentials!'
print('CORS config: PASS')
"
```

- [ ] **Step 4: Commit**

---

## 2. P1 — 架构与性能

### Task 2.1: T07 — 移除 Router 内 Celery 同步阻塞

**Spec:** `openspec/changes/code-quality-remediation/specs/async-task-orchestration/spec.md`

- [ ] **Step 1: Replace task.get(timeout=120) calls**
In `api/generate.py`, find lines with `task.get(timeout=120)` (~201, 222, 242) and remove them — the `delay()` calls above already return task_id. No synchronous wait is needed.

- [ ] **Step 2: Verify**
```bash
cd ArticleGeneratorService && grep "task\.get" app/api/generate.py
# Expected: no output
```

- [ ] **Step 3: Commit**

---

### Task 2.2: T08 — 抽取 Service 层

**Spec:** `openspec/changes/code-quality-remediation/specs/service-layer/spec.md`

- [ ] **Step 1: Create services/generate_service.py**
Move trigger logic from `api/generate.py` to `services/generate_service.py`. Router functions become thin wrappers.

- [ ] **Step 2: Create services/article_service.py**
Move status machine logic (approve/reject/publish transitions).

- [ ] **Step 3: Slim down api/generate.py and api/articles.py**
Router functions should be ≤30 lines.

- [ ] **Step 4: Run pytest and commit**

---

### Task 2.3: T09 — 拆分 Celery tasks

**Spec:** `openspec/changes/code-quality-remediation/specs/celery-task-split/spec.md`

- [ ] **Step 1: Create app/celery_app.py**
Extract Celery instance from tasks.py.

- [ ] **Step 2: Create app/tasks/ package**
`tasks/__init__.py`, `tasks/generate.py`, `tasks/review.py`, `tasks/distill.py`.

- [ ] **Step 3: Create utils/json_parse.py**
Extract repeated JSON parsing logic.

- [ ] **Step 4: Delete old app/tasks.py**
- [ ] **Step 5: Verify worker starts and commit**

---

### Task 2.4: T10 — 前端 API 层重构

**Spec:** `openspec/changes/code-quality-remediation/specs/frontend-api-refactor/spec.md`

- [ ] **Step 1: Extract domain API modules**
Create `api/hotspots.ts`, `articles.ts`, `accounts.ts`, `tasks.ts`, `providers.ts`.

- [ ] **Step 2: Create api/index.ts** with aggregated exports.
- [ ] **Step 3: Update all view imports** to use new modules.
- [ ] **Step 4: Verify npm run build passes** and commit.

---

### Task 2.5: T11 — 抽取核心前端组件与 hooks

**Spec:** `openspec/changes/code-quality-remediation/specs/shared-components-hooks/spec.md`

- [ ] **Step 1: Create ArticleEditorDialog.vue**
- [ ] **Step 2: Create PageHeader.vue**
- [ ] **Step 3: Create hooks/usePaginatedList.ts**
- [ ] **Step 4: Create hooks/useActiveTasks.ts**
- [ ] **Step 5: Refactor views to use shared components**
- [ ] **Step 6: Verify App.vue < 250 lines** and commit.

---

### Task 2.6: T12 — 启用 Pinia Store

**Spec:** `openspec/changes/code-quality-remediation/specs/pinia-store/spec.md`

- [ ] **Step 1: Create store/accounts.ts**
- [ ] **Step 2: Create store/tasks.ts**
- [ ] **Step 3: Replace per-view account/task fetching with store**
- [ ] **Step 4: Verify and commit**

---

### Task 2.7: T13 — 无效 hotspot_id 显式错误

**Spec:** `openspec/changes/code-quality-remediation/specs/input-validation/spec.md`

- [ ] **Step 1: Add validation in generate trigger**
Check all `hotspot_ids` at the start; return 400 + `{detail, invalid_ids: [...]}` for any missing.

- [ ] **Step 2: Add test case**
`tests/test_generate.py`: assert 400 with invalid IDs.

- [ ] **Step 3: Run tests and commit**

---

## 3. P2 — 一致性、测试与 DB

### Task 3.1–3.9: T14–T22

Each task follows the same pattern: reference spec → modify/create files → run tests → commit.

| Task | Key Files | Verification |
|------|-----------|--------------|
| T14 | `scripts/start.sh`, `docker-compose.yml` | Empty DB startup matches migrations |
| T15 | `app/models/*.py`, `app/schemas/*.py` | All imports remain valid, pytest green |
| T16 | `tests/test_providers.py`, `test_auth.py`, `conftest.py` | `pytest tests/ -v` all pass |
| T17 | `LLMService/tests/test_api.py`, `test_gateway.py` | `cd LLMService && pytest` pass |
| T18 | `router.test.ts`, `format.test.ts`, `package.json` | `npm run test && npm run typecheck` pass |
| T19 | All views (PageHeader + v-loading) | No `#f5f7fa`, consistent UI |
| T20 | `LLMService/app/adapters/`, `generator.py` | grep finds no dead code refs |
| T21 | `app/constants.py`, `app/enums.py` | No magic strings in business code |
| T22 | `app/logging_config.py`, all `*.py` | No `print()` in prod paths |

---

## 4. P3 — 优化与文档

### Task 4.1–4.5: T23–T27

| Task | Key Files | Verification |
|------|-----------|--------------|
| T23 | ADR or README | Documented single recommended API |
| T24 | `styles/layout.css`, `components/layout/AppSidebar.vue`, `TaskCenterBell.vue` | App.vue composition-focused |
| T25 | `hooks/useCrudDialog.ts` | 3 CRUD pages reduced 30%+ |
| T26 | `index.html`, sidebar, `ArticleGeneratorAdm/README.md` | "墨斋" consistent |
| T27 | `tasks/` (autoretry_for), docs | Retry config functional |

---

## 自检清单

- [x] 每个 capability spec 有对应任务
- [x] 无 TBD/TODO/占位符
- [x] 文件路径精确
- [x] T01 为最详细任务（基础），后续任务渐进式简略（参考 spec + design 即可执行）
- [x] P0 任务 T01-T06 有完整 step-by-step
