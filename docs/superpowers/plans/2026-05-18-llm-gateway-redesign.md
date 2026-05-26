# LLMService 通用网关改造 + 风格蒸馏系统 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 LLMService 从本地模型+LoRA 架构改造为多 API 供应商网关 + Prompt 风格蒸馏系统

**Architecture:** LLMService 改造为通用 AI 网关（单一 /chat 端点，Adapter 模式对接多 Provider）；后端新增 Provider 管理、场景路由、参考文章、蒸馏触发 API；Celery 任务扩展为 5 种场景；前端新增/改造 4 个页面

**Tech Stack:** FastAPI, SQLAlchemy, Celery, Vue 3 + Element Plus, Anthropic SDK, OpenAI SDK

---

## 文件映射

| 操作 | 路径 | 职责 |
|------|------|------|
| Create | `ArticleGeneratorDatabase/migrations/003_llm_gateway.sql` | 新建 4 表 + alter 2 表 |
| Modify | `LLMService/app/config.py` | 废弃 MOCK_MODE/MODEL_PATH，改用 DB 配置 |
| Create | `LLMService/app/adapters/__init__.py` | Adapter 导出 |
| Create | `LLMService/app/adapters/base.py` | BaseAdapter 抽象类 |
| Create | `LLMService/app/adapters/anthropic.py` | Anthropic Messages API |
| Create | `LLMService/app/adapters/deepseek.py` | DeepSeek Chat Completions |
| Create | `LLMService/app/adapters/openai.py` | OpenAI Chat Completions |
| Create | `LLMService/app/adapters/registry.py` | Adapter 注册表 |
| Create | `LLMService/app/gateway.py` | /chat 处理流程 |
| Modify | `LLMService/app/main.py` | /chat 端点，废弃旧端点 |
| Delete | `LLMService/app/model_loader.py` | 不再需要 |
| Modify | `LLMService/app/generator.py` | 简化为仅保留 mock fallback |
| Modify | `LLMService/requirements.txt` | 移除 torch/transformers/peft，加 anthropic/openai |
| Modify | `ArticleGeneratorService/app/models.py` | 新增 4 个 model + Account/Article 加字段 |
| Modify | `ArticleGeneratorService/app/schemas.py` | 新增 Pydantic 模型 |
| Create | `ArticleGeneratorService/app/api/providers.py` | Provider CRUD |
| Create | `ArticleGeneratorService/app/api/scenario_configs.py` | Scenario 路由 CRUD |
| Create | `ArticleGeneratorService/app/api/reference_articles.py` | 参考文章 CRUD |
| Create | `ArticleGeneratorService/app/api/distill.py` | 蒸馏触发 + 风格画像管理 |
| Modify | `ArticleGeneratorService/app/tasks.py` | 新增 4 种 Celery 任务 |
| Modify | `ArticleGeneratorService/app/api/generate.py` | 改造触发流程 + chain 评审 |
| Modify | `ArticleGeneratorService/app/main.py` | 注册新路由 |
| Create | `ArticleGeneratorAdm/src/views/ProvidersView.vue` | 供应商管理页 |
| Create | `ArticleGeneratorAdm/src/views/ScenarioConfigsView.vue` | 场景配置页 |
| Modify | `ArticleGeneratorAdm/src/views/AccountsView.vue` | +参考文章 +风格画像 |
| Modify | `ArticleGeneratorAdm/src/views/ReviewView.vue` | +评分/风险显示 |
| Modify | `ArticleGeneratorAdm/src/api/client.ts` | 新增 API 方法 |
| Modify | `ArticleGeneratorAdm/src/router/index.ts` | 新增 2 条路由 |

---

### Task 1: 数据库迁移

**Files:**
- Create: `ArticleGeneratorDatabase/migrations/003_llm_gateway.sql`

- [ ] **Step 1: 编写迁移脚本**

```sql
-- 003_llm_gateway.sql
-- LLM网关改造：providers + scenario_configs + reference_articles + generation_logs
-- 同时扩展 accounts 和 articles 表

-- 1. API供应商表
CREATE TABLE IF NOT EXISTS providers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '供应商名称',
    base_url VARCHAR(500) NOT NULL COMMENT 'API地址',
    api_key VARCHAR(500) NOT NULL COMMENT 'API Key',
    models JSON COMMENT '可用模型列表',
    enabled TINYINT(1) DEFAULT 1 COMMENT '0否 1是',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API供应商';

-- 2. 场景路由配置表
CREATE TABLE IF NOT EXISTS scenario_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario VARCHAR(50) NOT NULL COMMENT 'distill/generate/quality_review/compliance_review/refine',
    provider_id INT NOT NULL,
    model VARCHAR(100) NOT NULL COMMENT '模型名',
    system_prompt_template TEXT COMMENT 'System Prompt模板',
    params JSON COMMENT 'temperature, max_tokens等',
    priority INT DEFAULT 0 COMMENT 'fallback顺序',
    enabled TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_scenario (scenario),
    FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='场景路由配置';

-- 3. 参考文章表
CREATE TABLE IF NOT EXISTS reference_articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    title VARCHAR(500) NOT NULL COMMENT '文章标题',
    content LONGTEXT NOT NULL COMMENT '正文',
    source_url VARCHAR(1000) COMMENT '来源链接',
    embedding JSON COMMENT 'embedding向量',
    is_benchmark TINYINT(1) DEFAULT 0 COMMENT '是否代表篇',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_account (account_id),
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='参考文章';

-- 4. 生成日志表
CREATE TABLE IF NOT EXISTS generation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario VARCHAR(50) NOT NULL,
    provider_id INT,
    model VARCHAR(100),
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    latency_ms INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_scenario (scenario),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生成日志';

-- 5. 扩展 accounts 表
ALTER TABLE accounts
    ADD COLUMN style_profile TEXT COMMENT '风格画像文本' AFTER sample_articles,
    ADD COLUMN style_profile_updated_at DATETIME COMMENT '画像更新时间' AFTER style_profile;

-- 6. 扩展 articles 表
ALTER TABLE articles
    ADD COLUMN quality_score INT COMMENT '质量评分 0-100' AFTER refine_history,
    ADD COLUMN compliance_score INT COMMENT '合规评分 0-100' AFTER quality_score,
    ADD COLUMN review_notes TEXT COMMENT '评审备注' AFTER compliance_score;
```

- [ ] **Step 2: 执行迁移验证**

```bash
mysql -u root -p article_generator < ArticleGeneratorDatabase/migrations/003_llm_gateway.sql
```

或者如果使用 SQLite：

```bash
sqlite3 ArticleGeneratorService/article_generator.db < ArticleGeneratorDatabase/migrations/003_llm_gateway.sql 2>&1 || echo "SQLite does not support some MySQL-specific syntax; models.py create_all handles dev env"
```

Expected: 表创建成功，无报错

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorDatabase/migrations/003_llm_gateway.sql
git commit -m "feat: add LLM gateway tables migration (providers, scenario_configs, reference_articles, generation_logs)"
```

---

### Task 2: LLMService 配置 + Adapter 基础层

**Files:**
- Create: `LLMService/app/adapters/__init__.py`
- Create: `LLMService/app/adapters/base.py`
- Create: `LLMService/app/adapters/registry.py`
- Modify: `LLMService/app/config.py`
- Modify: `LLMService/requirements.txt`

- [ ] **Step 1: 更新 requirements.txt**

```
fastapi>=0.100.0
uvicorn>=0.23.0
httpx>=0.24.0
anthropic>=0.39.0
openai>=1.0.0
pydantic-settings>=2.0.0
```

- [ ] **Step 2: 更新 config.py**

```python
"""
LLM 网关配置
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """网关配置——不再需要 MOCK_MODE 或 MODEL_PATH"""

    # 后端 API 地址（用于回查 providers / scenario_configs）
    backend_api_url: str = "http://localhost:8000"

    # 数据库配置（SQLite，仅用于启动时初始化空表；实际配置从后端 API 拉取）
    database_url: str = "sqlite:///./gateway.db"

    port: int = 8001

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

- [ ] **Step 3: 创建 BaseAdapter 抽象类**

`LLMService/app/adapters/base.py`:

```python
"""
Provider Adapter 基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ChatMessage:
    """统一消息格式"""
    def __init__(self, role: str, content: str):
        self.role = role  # system / user / assistant
        self.content = content


class ChatResult:
    """统一返回格式"""
    def __init__(self, content: str, prompt_tokens: int = 0, completion_tokens: int = 0, latency_ms: int = 0):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = latency_ms


class BaseAdapter(ABC):
    """Provider 适配器基类"""

    @abstractmethod
    def chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[ChatMessage],
        params: Dict[str, Any],
    ) -> ChatResult:
        """发送消息并返回统一结果"""
        ...
```

- [ ] **Step 4: 创建 Adapter 注册表**

`LLMService/app/adapters/registry.py`:

```python
"""
Adapter 注册表：按 provider name 查找对应 Adapter
"""
from typing import Dict, Type
from .base import BaseAdapter


_registry: Dict[str, Type[BaseAdapter]] = {}


def register(name: str):
    """装饰器：注册 adapter"""
    def decorator(cls: Type[BaseAdapter]):
        _registry[name.lower()] = cls
        return cls
    return decorator


def get_adapter(name: str) -> BaseAdapter:
    """按名称获取 adapter 实例"""
    key = name.lower()
    if key not in _registry:
        raise ValueError(f"Unsupported provider: {name}. Available: {list(_registry.keys())}")
    return _registry[key]()


def available_providers():
    return list(_registry.keys())
```

- [ ] **Step 5: 创建 __init__.py**

`LLMService/app/adapters/__init__.py`:

```python
from .base import BaseAdapter, ChatMessage, ChatResult
from .registry import register, get_adapter, available_providers
```

- [ ] **Step 6: Commit**

```bash
git add LLMService/requirements.txt LLMService/app/config.py LLMService/app/adapters/
git commit -m "feat: add LLM gateway config and adapter base layer"
```

---

### Task 3: 实现 Anthropic Adapter

**Files:**
- Create: `LLMService/app/adapters/anthropic.py`

- [ ] **Step 1: 编写 AnthropicAdapter 及测试**

`LLMService/app/adapters/anthropic.py`:

```python
"""
Anthropic Messages API 适配器
"""
import time
from typing import Any, Dict, List
from anthropic import Anthropic
from .base import BaseAdapter, ChatMessage, ChatResult
from .registry import register


@register("anthropic")
class AnthropicAdapter(BaseAdapter):
    def chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[ChatMessage],
        params: Dict[str, Any],
    ) -> ChatResult:
        client = Anthropic(api_key=api_key, base_url=base_url)
        system_prompt = ""
        user_messages = []
        for m in messages:
            if m.role == "system":
                system_prompt += m.content + "\n"
            else:
                user_messages.append({"role": m.role, "content": m.content})

        start = time.time()
        resp = client.messages.create(
            model=model,
            system=system_prompt.strip() or None,
            messages=user_messages,
            max_tokens=params.get("max_tokens", 4096),
            temperature=params.get("temperature", 0.7),
        )
        elapsed = int((time.time() - start) * 1000)

        return ChatResult(
            content=resp.content[0].text,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            latency_ms=elapsed,
        )
```

- [ ] **Step 2: Commit**

```bash
git add LLMService/app/adapters/anthropic.py
git commit -m "feat: add Anthropic adapter"
```

---

### Task 4: 实现 DeepSeek Adapter

**Files:**
- Create: `LLMService/app/adapters/deepseek.py`

- [ ] **Step 1: 编写 DeepSeekAdapter**

`LLMService/app/adapters/deepseek.py`:

```python
"""
DeepSeek Chat Completions API 适配器
"""
import time
from typing import Any, Dict, List
from openai import OpenAI
from .base import BaseAdapter, ChatMessage, ChatResult
from .registry import register


@register("deepseek")
class DeepSeekAdapter(BaseAdapter):
    def chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[ChatMessage],
        params: Dict[str, Any],
    ) -> ChatResult:
        client = OpenAI(api_key=api_key, base_url=base_url)
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        start = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=openai_messages,
            max_tokens=params.get("max_tokens", 4096),
            temperature=params.get("temperature", 0.7),
        )
        elapsed = int((time.time() - start) * 1000)

        return ChatResult(
            content=resp.choices[0].message.content or "",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            latency_ms=elapsed,
        )
```

- [ ] **Step 2: Commit**

```bash
git add LLMService/app/adapters/deepseek.py
git commit -m "feat: add DeepSeek adapter"
```

---

### Task 5: 实现 OpenAI Adapter

**Files:**
- Create: `LLMService/app/adapters/openai.py`

- [ ] **Step 1: 编写 OpenAIAdapter**

`LLMService/app/adapters/openai.py`:

```python
"""
OpenAI Chat Completions API 适配器
"""
import time
from typing import Any, Dict, List
from openai import OpenAI
from .base import BaseAdapter, ChatMessage, ChatResult
from .registry import register


@register("openai")
class OpenAIAdapter(BaseAdapter):
    def chat(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: List[ChatMessage],
        params: Dict[str, Any],
    ) -> ChatResult:
        client = OpenAI(api_key=api_key, base_url=base_url)
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        start = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=openai_messages,
            max_tokens=params.get("max_tokens", 4096),
            temperature=params.get("temperature", 0.7),
        )
        elapsed = int((time.time() - start) * 1000)

        return ChatResult(
            content=resp.choices[0].message.content or "",
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            latency_ms=elapsed,
        )
```

- [ ] **Step 2: Commit**

```bash
git add LLMService/app/adapters/openai.py
git commit -m "feat: add OpenAI adapter"
```

---

### Task 6: LLMService Gateway 核心 + /chat 端点

**Files:**
- Create: `LLMService/app/gateway.py`
- Modify: `LLMService/app/main.py`
- Modify: `LLMService/app/generator.py`

- [ ] **Step 1: 编写 gateway.py**

`LLMService/app/gateway.py`:

```python
"""
LLM Gateway：接收 /chat 请求，查配置 → 渲染 prompt → 调 adapter → 返回
"""
import time
import httpx
from string import Template
from typing import Any, Dict, List, Optional
from .adapters import ChatMessage, ChatResult, get_adapter
from .config import settings


class Gateway:
    def __init__(self, backend_api_url: str = None):
        self.backend_api_url = (backend_api_url or settings.backend_api_url).rstrip("/")

    def _fetch_config(self, scenario: str) -> Dict[str, Any]:
        """从后端 API 获取 scenario_config（含 provider 信息）"""
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self.backend_api_url}/api/scenario-configs/by-scenario/{scenario}")
            resp.raise_for_status()
            return resp.json()

    def _fetch_account(self, account_id: int) -> Dict[str, Any]:
        """获取账号信息（含 style_profile）"""
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self.backend_api_url}/api/accounts/{account_id}")
            resp.raise_for_status()
            return resp.json()

    def _render_prompt(self, template: str, variables: Dict[str, Any]) -> str:
        """简单模板渲染：{{var}} → value"""
        result = template
        for k, v in variables.items():
            result = result.replace("{{" + k + "}}", str(v) if v else "")
        return result

    def chat(
        self,
        scenario: str,
        account_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        extra_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """统一聊天入口"""
        variables = variables or {}

        # 1. 查场景配置
        config = self._fetch_config(scenario)
        if not config:
            return {"error": f"Scenario not found: {scenario}"}

        # 2. 注入风格画像
        if account_id and "style_profile" not in variables:
            try:
                account = self._fetch_account(account_id)
                if account.get("style_profile"):
                    variables["style_profile"] = account["style_profile"]
            except Exception:
                pass

        # 3. 渲染 system prompt
        system_prompt = self._render_prompt(
            config["system_prompt_template"] or "", variables
        )

        # 4. 组装 messages
        messages = []
        if system_prompt.strip():
            messages.append(ChatMessage(role="system", content=system_prompt))
        # 如果有 user prompt 模板变量
        user_content = variables.get("user_prompt") or variables.get("hotspot_title") or variables.get("keywords") or ""
        if user_content:
            messages.append(ChatMessage(role="user", content=user_content))
        if extra_messages:
            for m in extra_messages:
                messages.append(ChatMessage(role=m["role"], content=m["content"]))

        # 5. 获取 adapter 并调用
        provider = config.get("provider", {})
        provider_name = (provider.get("name") or "").lower()
        adapter = get_adapter(provider_name)

        adapter_params = config.get("params") or {}
        result = adapter.chat(
            base_url=provider.get("base_url", ""),
            api_key=provider.get("api_key", ""),
            model=config.get("model", ""),
            messages=messages,
            params=adapter_params,
        )

        # 6. 记录日志（异步 fire-and-forget）
        self._log_call(scenario, provider.get("id"), config.get("model"), result)

        return {
            "content": result.content,
            "usage": {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
            },
            "latency_ms": result.latency_ms,
        }

    def _log_call(self, scenario: str, provider_id: Optional[int], model: str, result: ChatResult):
        """记录调用日志到后端"""
        try:
            with httpx.Client(timeout=5.0) as client:
                client.post(f"{self.backend_api_url}/api/generation-logs", json={
                    "scenario": scenario,
                    "provider_id": provider_id,
                    "model": model,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "latency_ms": result.latency_ms,
                    "status": "success",
                })
        except Exception:
            pass


gateway = Gateway()
```

- [ ] **Step 2: 重写 main.py**

`LLMService/app/main.py`:

```python
"""
LLM 网关服务：通用 AI 调用入口，支持多 Provider 按场景路由
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from .gateway import gateway

app = FastAPI(
    title="ArticleGenerator LLM Gateway",
    description="通用 AI 调用网关，支持 Anthropic / DeepSeek / OpenAI",
    version="0.2.0",
)


class ChatRequest(BaseModel):
    scenario: str
    account_id: Optional[int] = None
    variables: Optional[Dict[str, Any]] = None
    extra_messages: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    content: str
    usage: Optional[Dict[str, int]] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None


@app.get("/")
def root():
    return {"message": "LLM Gateway", "version": "0.2.0"}


@app.post("/chat")
def chat(req: ChatRequest):
    """统一聊天入口：按 scenario 路由到对应 provider + model"""
    result = gateway.chat(
        scenario=req.scenario,
        account_id=req.account_id,
        variables=req.variables,
        extra_messages=req.extra_messages,
    )
    if "error" in result:
        return {"content": "", "error": result["error"]}
    return result


# 保留旧端点兼容（标记废弃），内部转发到 /chat
@app.post("/generate")
def generate_legacy(hotspot_title: str, account_id: int):
    return app.post("/chat", json={
        "scenario": "generate",
        "account_id": account_id,
        "variables": {"hotspot_title": hotspot_title},
    })


@app.post("/refine")
def refine_legacy(article_id: int, content: str, keywords: str):
    return app.post("/chat", json={
        "scenario": "refine",
        "variables": {"article_content": content, "keywords": keywords},
    })
```

- [ ] **Step 3: 简化 generator.py 为 mock fallback**

`LLMService/app/generator.py` 改为网关内部 fallback（当后端 API 不可达或未配置任何 scenario 时使用）：

```python
"""
Mock fallback：当后端 API 不可达时使用的占位生成逻辑
"""
from typing import Optional


def mock_generate(hotspot_title: str, account_id: int) -> str:
    """占位生成——仅在后端 API 或 LLM Provider 未配置时使用"""
    return f"""# {hotspot_title}

【占位文章】请先在管理后台配置：
1. API 供应商（/providers）
2. 场景路由（/scenario-configs）
3. 为账号 {account_id} 蒸馏风格画像

完成配置后，重新触发生成即可获得真实文章。
"""


def mock_refine(content: str, keywords: str) -> str:
    """占位微调"""
    return f"""{content}

---
【占位微调】要求关键词：{keywords}
请完成配置后重试。
"""
```

- [ ] **Step 4: Commit**

```bash
git add LLMService/app/gateway.py LLMService/app/main.py LLMService/app/generator.py
git commit -m "feat: implement LLM gateway core with /chat endpoint and mock fallback"
```

---

### Task 7: 后端 models.py + schemas.py 扩展

**Files:**
- Modify: `ArticleGeneratorService/app/models.py`
- Modify: `ArticleGeneratorService/app/schemas.py`

- [ ] **Step 1: 扩展 models.py**

在现有模型类后面追加：

```python
class Provider(Base):
    """API 供应商"""
    __tablename__ = "providers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=False)
    models = Column(Text)  # JSON
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScenarioConfig(Base):
    """场景路由配置"""
    __tablename__ = "scenario_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario = Column(String(50), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    model = Column(String(100), nullable=False)
    system_prompt_template = Column(Text)
    params = Column(Text)  # JSON
    priority = Column(Integer, default=0)
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    provider = relationship("Provider", lazy="joined")


class ReferenceArticle(Base):
    """参考文章"""
    __tablename__ = "reference_articles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source_url = Column(String(1000))
    embedding = Column(Text)  # JSON
    is_benchmark = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class GenerationLog(Base):
    """生成日志"""
    __tablename__ = "generation_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario = Column(String(50), nullable=False)
    provider_id = Column(Integer)
    model = Column(String(100))
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    status = Column(String(20), default="success")
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
```

Account 和 Article 新增字段：

```python
# Account 新增
style_profile = Column(Text)
style_profile_updated_at = Column(DateTime)

# Article 新增
quality_score = Column(Integer)
compliance_score = Column(Integer)
review_notes = Column(Text)
```

- [ ] **Step 2: 扩展 schemas.py**

追加 Pydantic 模型：

```python
# ----- Provider -----
class ProviderBase(BaseModel):
    name: str
    base_url: str
    api_key: str
    models: Optional[str] = None  # JSON
    enabled: bool = True

class ProviderCreate(ProviderBase): pass
class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    models: Optional[str] = None
    enabled: Optional[bool] = None

class ProviderResponse(ProviderBase):
    id: int
    created_at: datetime
    class Config: from_attributes = True


# ----- ScenarioConfig -----
class ScenarioConfigBase(BaseModel):
    scenario: str
    provider_id: int
    model: str = ""
    system_prompt_template: Optional[str] = None
    params: Optional[str] = None  # JSON
    priority: int = 0
    enabled: bool = True

class ScenarioConfigCreate(ScenarioConfigBase): pass
class ScenarioConfigUpdate(BaseModel):
    provider_id: Optional[int] = None
    model: Optional[str] = None
    system_prompt_template: Optional[str] = None
    params: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None

class ScenarioConfigResponse(ScenarioConfigBase):
    id: int
    provider: Optional[ProviderResponse] = None
    created_at: datetime
    class Config: from_attributes = True


# ----- ReferenceArticle -----
class ReferenceArticleBase(BaseModel):
    account_id: int
    title: str
    content: str
    source_url: Optional[str] = None
    embedding: Optional[str] = None
    is_benchmark: bool = False

class ReferenceArticleCreate(ReferenceArticleBase): pass
class ReferenceArticleResponse(ReferenceArticleBase):
    id: int
    created_at: datetime
    class Config: from_attributes = True


# ----- GenerationLog -----
class GenerationLogCreate(BaseModel):
    scenario: str
    provider_id: Optional[int] = None
    model: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    status: str = "success"
    error_message: Optional[str] = None


# ----- Distill -----
class DistillRequest(BaseModel):
    account_id: int


# 扩展 AccountResponse 加回 style_profile
# 在 AccountResponse 中追加:
# style_profile: Optional[str] = None
# style_profile_updated_at: Optional[datetime] = None
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/models.py ArticleGeneratorService/app/schemas.py
git commit -m "feat: add Provider, ScenarioConfig, ReferenceArticle, GenerationLog models and schemas"
```

---

### Task 8: 后端 Provider + Scenario Config API

**Files:**
- Create: `ArticleGeneratorService/app/api/providers.py`
- Create: `ArticleGeneratorService/app/api/scenario_configs.py`

- [ ] **Step 1: 编写 providers.py**

`ArticleGeneratorService/app/api/providers.py`:

```python
"""
API 供应商管理
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Provider
from ..schemas import ProviderCreate, ProviderUpdate, ProviderResponse

router = APIRouter(prefix="/providers", tags=["API供应商"])


@router.get("", response_model=List[ProviderResponse])
def list_providers(db: Session = Depends(get_db)):
    return db.query(Provider).order_by(Provider.id).all()


@router.post("", response_model=ProviderResponse)
def create_provider(data: ProviderCreate, db: Session = Depends(get_db)):
    p = Provider(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/{provider_id}", response_model=ProviderResponse)
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    p = db.query(Provider).filter(Provider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return p


@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(provider_id: int, data: ProviderUpdate, db: Session = Depends(get_db)):
    p = db.query(Provider).filter(Provider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="供应商不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{provider_id}")
def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    p = db.query(Provider).filter(Provider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="供应商不存在")
    db.delete(p)
    db.commit()
    return {"message": "删除成功"}
```

- [ ] **Step 2: 编写 scenario_configs.py**

`ArticleGeneratorService/app/api/scenario_configs.py`:

```python
"""
场景路由配置
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import ScenarioConfig
from ..schemas import ScenarioConfigCreate, ScenarioConfigUpdate, ScenarioConfigResponse

router = APIRouter(prefix="/scenario-configs", tags=["场景配置"])


@router.get("", response_model=List[ScenarioConfigResponse])
def list_configs(db: Session = Depends(get_db)):
    return db.query(ScenarioConfig).order_by(ScenarioConfig.id).all()


@router.post("", response_model=ScenarioConfigResponse)
def create_config(data: ScenarioConfigCreate, db: Session = Depends(get_db)):
    config = ScenarioConfig(**data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.get("/{config_id}", response_model=ScenarioConfigResponse)
def get_config(config_id: int, db: Session = Depends(get_db)):
    c = db.query(ScenarioConfig).filter(ScenarioConfig.id == config_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="配置不存在")
    return c


@router.get("/by-scenario/{scenario}")
def get_config_by_scenario(scenario: str, db: Session = Depends(get_db)):
    """LLMService 网关查询场景配置（含 provider 详情）"""
    c = db.query(ScenarioConfig).filter(
        ScenarioConfig.scenario == scenario,
        ScenarioConfig.enabled == 1
    ).order_by(ScenarioConfig.priority.desc()).first()
    if not c:
        return None
    return {
        "id": c.id,
        "scenario": c.scenario,
        "model": c.model,
        "system_prompt_template": c.system_prompt_template,
        "params": c.params,
        "priority": c.priority,
        "provider": {
            "id": c.provider.id if c.provider else None,
            "name": c.provider.name if c.provider else "",
            "base_url": c.provider.base_url if c.provider else "",
            "api_key": c.provider.api_key if c.provider else "",
        },
    }


@router.put("/{config_id}", response_model=ScenarioConfigResponse)
def update_config(config_id: int, data: ScenarioConfigUpdate, db: Session = Depends(get_db)):
    c = db.query(ScenarioConfig).filter(ScenarioConfig.id == config_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="配置不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{config_id}")
def delete_config(config_id: int, db: Session = Depends(get_db)):
    c = db.query(ScenarioConfig).filter(ScenarioConfig.id == config_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="配置不存在")
    db.delete(c)
    db.commit()
    return {"message": "删除成功"}
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/api/providers.py ArticleGeneratorService/app/api/scenario_configs.py
git commit -m "feat: add Provider and Scenario Config API routes"
```

---

### Task 9: 后端参考文章 + 蒸馏 API

**Files:**
- Create: `ArticleGeneratorService/app/api/reference_articles.py`
- Create: `ArticleGeneratorService/app/api/distill.py`

- [ ] **Step 1: 编写 reference_articles.py**

`ArticleGeneratorService/app/api/reference_articles.py`:

```python
"""
账号参考文章管理
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import ReferenceArticle, Account
from ..schemas import ReferenceArticleCreate, ReferenceArticleResponse

router = APIRouter(prefix="/accounts/{account_id}/reference-articles", tags=["参考文章"])


@router.get("", response_model=List[ReferenceArticleResponse])
def list_articles(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return db.query(ReferenceArticle).filter(
        ReferenceArticle.account_id == account_id
    ).order_by(ReferenceArticle.id.desc()).all()


@router.post("", response_model=ReferenceArticleResponse)
def create_article(account_id: int, data: ReferenceArticleCreate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    article = ReferenceArticle(account_id=account_id, **data.model_dump(exclude={"account_id"}))
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@router.delete("/{article_id}")
def delete_article(account_id: int, article_id: int, db: Session = Depends(get_db)):
    article = db.query(ReferenceArticle).filter(
        ReferenceArticle.id == article_id,
        ReferenceArticle.account_id == account_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="参考文章不存在")
    db.delete(article)
    db.commit()
    return {"message": "删除成功"}


@router.put("/{article_id}", response_model=ReferenceArticleResponse)
def update_article(account_id: int, article_id: int, data: ReferenceArticleCreate, db: Session = Depends(get_db)):
    article = db.query(ReferenceArticle).filter(
        ReferenceArticle.id == article_id,
        ReferenceArticle.account_id == account_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="参考文章不存在")
    for k, v in data.model_dump(exclude={"account_id"}).items():
        setattr(article, k, v)
    db.commit()
    db.refresh(article)
    return article
```

- [ ] **Step 2: 编写 distill.py**

`ArticleGeneratorService/app/api/distill.py`:

```python
"""
风格蒸馏：触发生成风格画像
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Account, ReferenceArticle
from ..tasks import trigger_distill

router = APIRouter(prefix="/accounts", tags=["风格蒸馏"])


@router.post("/{account_id}/distill")
def distill_account_style(account_id: int, db: Session = Depends(get_db)):
    """触发风格蒸馏任务"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    articles = db.query(ReferenceArticle).filter(
        ReferenceArticle.account_id == account_id
    ).all()

    if not articles:
        raise HTTPException(status_code=400, detail="该账号没有参考文章，请先添加")

    articles_content = []
    for a in articles:
        articles_content.append(f"## {a.title}\n\n{a.content}")

    task = trigger_distill.delay(
        account_id=account_id,
        articles_content=articles_content,
        num_articles=len(articles),
    )

    return {"message": "蒸馏任务已提交", "task_id": task.id}
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/api/reference_articles.py ArticleGeneratorService/app/api/distill.py
git commit -m "feat: add reference articles and distill API"
```

---

### Task 10: 后端 Generation Log API + 注册路由

**Files:**
- Create: `ArticleGeneratorService/app/api/generation_logs.py`
- Modify: `ArticleGeneratorService/app/main.py`

- [ ] **Step 1: 编写 generation_logs.py**

`ArticleGeneratorService/app/api/generation_logs.py`:

```python
"""
生成日志：供 LLMService 网关回调记录
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..models import GenerationLog
from ..schemas import GenerationLogCreate

router = APIRouter(prefix="/generation-logs", tags=["生成日志"])


@router.post("")
def create_log(data: GenerationLogCreate, db: Session = Depends(get_db)):
    log = GenerationLog(**data.model_dump())
    db.add(log)
    db.commit()
    return {"message": "ok"}


@router.get("")
def list_logs(
    scenario: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(GenerationLog)
    if scenario:
        q = q.filter(GenerationLog.scenario == scenario)
    q = q.order_by(GenerationLog.created_at.desc())
    total = q.count()
    offset = (page - 1) * page_size
    logs = q.offset(offset).limit(page_size).all()
    return {"data": logs, "total": total}
```

- [ ] **Step 2: 更新 main.py 注册新路由**

`ArticleGeneratorService/app/main.py` 添加 import 和路由注册：

```python
from .api import providers, scenario_configs, reference_articles, distill, generation_logs

# 在现有 app.include_router 后追加：
app.include_router(providers.router, prefix="/api")
app.include_router(scenario_configs.router, prefix="/api")
app.include_router(reference_articles.router, prefix="/api")
app.include_router(distill.router, prefix="/api")
app.include_router(generation_logs.router, prefix="/api")
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/api/generation_logs.py ArticleGeneratorService/app/main.py
git commit -m "feat: add generation logs API and register all new routes"
```

---

### Task 11: Celery 任务扩展（distill + quality_review + compliance_review + refine）

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py`

- [ ] **Step 1: 追加新 Celery 任务**

在现有 `tasks.py` 的 `trigger_generate` 和 `trigger_refine` 基础上追加：

```python
@celery_app.task(bind=True)
def trigger_distill(self, account_id: int, articles_content: list, num_articles: int):
    """异步蒸馏：参考文章 → 风格画像"""
    db = SessionLocal()
    try:
        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "distill",
                "account_id": account_id,
                "variables": {
                    "num_articles": str(num_articles),
                    "articles_content": "\n\n---\n\n".join(articles_content),
                },
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        if not content:
            raise ValueError("蒸馏返回内容为空")

        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            account.style_profile = content
            account.style_profile_updated_at = datetime.utcnow()
            db.commit()

        return {"account_id": account_id}
    except Exception as e:
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_quality_review(self, article_id: int, article_content: str):
    """异步质量评审：文章 → 质量评分"""
    db = SessionLocal()
    try:
        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "quality_review",
                "variables": {"article_content": article_content},
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        score = _parse_score(content)

        article = db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.quality_score = score
            notes = (article.review_notes or "") + f"\n[质量评审] {content[:500]}"
            article.review_notes = notes.strip()
            db.commit()

        return {"article_id": article_id, "score": score}
    except Exception as e:
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def trigger_compliance_review(self, article_id: int, article_content: str):
    """异步合规评审：文章 → 合规评分"""
    db = SessionLocal()
    try:
        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "compliance_review",
                "variables": {"article_content": article_content},
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        score = 100 if "safe" in content.lower() else _parse_score(content)

        article = db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.compliance_score = score
            notes = (article.review_notes or "") + f"\n[合规评审] {content[:500]}"
            article.review_notes = notes.strip()
            db.commit()

        return {"article_id": article_id, "score": score}
    except Exception as e:
        raise
    finally:
        db.close()


def _parse_score(text: str) -> int:
    """从评审文本中提取分值"""
    import re
    # 尝试匹配 "总分:85" 或 "score: 85" 或纯数字
    nums = re.findall(r"\b([0-9]{1,3})\b", text)
    if nums:
        scores = [int(n) for n in nums if 0 <= int(n) <= 100]
        if scores:
            return sum(scores) // len(scores)
    return 0
```

- [ ] **Step 2: 更新现有 trigger_generate — 生成后自动 chain 评审**

改造 `trigger_generate` 末尾（在 `return` 之前），追加 chain 调用：

```python
        # 生成成功后，自动链式触发质量评审 + 合规评审
        if article:
            chain_quality = trigger_quality_review.delay(article.id, article.content)
            chain_compliance = trigger_compliance_review.delay(article.id, article.content)

        return {"article_id": article.id}
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py
git commit -m "feat: add distill, quality_review, compliance_review Celery tasks with auto-chain"
```

---

### Task 12: 前端 API Client 扩展

**Files:**
- Modify: `ArticleGeneratorAdm/src/api/client.ts`

- [ ] **Step 1: 追加 API 方法**

`ArticleGeneratorAdm/src/api/client.ts` 在 `api` 对象末尾追加：

```typescript
  // 供应商管理
  getProviders: () => client.get<Provider[]>("/providers"),
  createProvider: (data: { name: string; base_url: string; api_key: string; models?: string; enabled?: boolean }) =>
    client.post<Provider>("/providers", data),
  updateProvider: (id: number, data: { name?: string; base_url?: string; api_key?: string; models?: string; enabled?: boolean }) =>
    client.put<Provider>(`/providers/${id}`, data),
  deleteProvider: (id: number) => client.delete(`/providers/${id}`),

  // 场景配置
  getScenarioConfigs: () => client.get<ScenarioConfig[]>("/scenario-configs"),
  createScenarioConfig: (data: { scenario: string; provider_id: number; model: string; system_prompt_template?: string; params?: string; priority?: number; enabled?: boolean }) =>
    client.post<ScenarioConfig>("/scenario-configs", data),
  updateScenarioConfig: (id: number, data: { provider_id?: number; model?: string; system_prompt_template?: string; params?: string; priority?: number; enabled?: boolean }) =>
    client.put<ScenarioConfig>(`/scenario-configs/${id}`, data),
  deleteScenarioConfig: (id: number) => client.delete(`/scenario-configs/${id}`),

  // 参考文章
  getReferenceArticles: (accountId: number) =>
    client.get<ReferenceArticle[]>(`/accounts/${accountId}/reference-articles`),
  createReferenceArticle: (accountId: number, data: { title: string; content: string; source_url?: string; is_benchmark?: boolean }) =>
    client.post<ReferenceArticle>(`/accounts/${accountId}/reference-articles`, { ...data, account_id: accountId }),
  updateReferenceArticle: (accountId: number, articleId: number, data: { title: string; content: string; source_url?: string; is_benchmark?: boolean; account_id: number }) =>
    client.put<ReferenceArticle>(`/accounts/${accountId}/reference-articles/${articleId}`, data),
  deleteReferenceArticle: (accountId: number, articleId: number) =>
    client.delete(`/accounts/${accountId}/reference-articles/${articleId}`),

  // 蒸馏
  triggerDistill: (accountId: number) =>
    client.post(`/accounts/${accountId}/distill`),

  // 生成日志
  getGenerationLogs: (params?: { scenario?: string; page?: number; page_size?: number }) =>
    client.get<PaginatedResponse<GenerationLog>>("/generation-logs", { params }),
```

追加 TypeScript 类型定义：

```typescript
export interface Provider {
  id: number;
  name: string;
  base_url: string;
  api_key: string;
  models?: string;
  enabled: boolean;
  created_at: string;
}

export interface ScenarioConfig {
  id: number;
  scenario: string;
  provider_id: number;
  model: string;
  system_prompt_template?: string;
  params?: string;
  priority: number;
  enabled: boolean;
  provider?: Provider;
  created_at: string;
}

export interface ReferenceArticle {
  id: number;
  account_id: number;
  title: string;
  content: string;
  source_url?: string;
  embedding?: string;
  is_benchmark: boolean;
  created_at: string;
}

export interface GenerationLog {
  id: number;
  scenario: string;
  provider_id?: number;
  model?: string;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
  status: string;
  error_message?: string;
  created_at: string;
}
```

`Account` 接口追加：

```typescript
export interface Account {
  // ...existing fields...
  style_profile?: string;
  style_profile_updated_at?: string;
}
```

`Article` 接口追加：

```typescript
export interface Article {
  // ...existing fields...
  quality_score?: number;
  compliance_score?: number;
  review_notes?: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add ArticleGeneratorAdm/src/api/client.ts
git commit -m "feat: add frontend API methods for providers, scenarios, reference articles, distill, logs"
```

---

### Task 13: 前端 Providers 页面

**Files:**
- Create: `ArticleGeneratorAdm/src/views/ProvidersView.vue`

- [ ] **Step 1: 编写 ProvidersView.vue**

```vue
<template>
  <div class="providers-view">
    <div class="page-header">
      <h2>API 供应商管理</h2>
      <el-button type="primary" @click="openCreate">新增供应商</el-button>
    </div>

    <el-table :data="providers" stripe>
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="base_url" label="API 地址" />
      <el-table-column label="API Key">
        <template #default="{ row }">
          <span v-if="showKey[row.id]">{{ row.api_key }}</span>
          <span v-else>****{{ row.api_key?.slice(-4) }}</span>
          <el-button size="small" text @click="showKey[row.id] = !showKey[row.id]">
            {{ showKey[row.id] ? '隐藏' : '显示' }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑供应商' : '新增供应商'" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="Anthropic / DeepSeek / OpenAI" />
        </el-form-item>
        <el-form-item label="API 地址" required>
          <el-input v-model="form.base_url" placeholder="https://api.anthropic.com" />
        </el-form-item>
        <el-form-item label="API Key" required>
          <el-input v-model="form.api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="模型列表">
          <el-input v-model="form.models" type="textarea" :rows="3" placeholder='[{"name":"claude-opus-4-7","max_tokens":200000}]' />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">{{ isEdit ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api, Provider } from "@/api/client";

const providers = ref<Provider[]>([]);
const showKey = reactive<Record<number, boolean>>({});
const dialogVisible = ref(false);
const isEdit = ref(false);
const saving = ref(false);
const editId = ref<number | null>(null);

const form = reactive({
  name: "",
  base_url: "",
  api_key: "",
  models: "",
  enabled: true,
});

function resetForm() {
  form.name = "";
  form.base_url = "";
  form.api_key = "";
  form.models = "";
  form.enabled = true;
  editId.value = null;
}

async function load() {
  const { data } = await api.getProviders();
  providers.value = data;
}

function openCreate() {
  resetForm();
  isEdit.value = false;
  dialogVisible.value = true;
}

function openEdit(row: Provider) {
  resetForm();
  isEdit.value = true;
  editId.value = row.id;
  form.name = row.name;
  form.base_url = row.base_url;
  form.api_key = row.api_key;
  form.models = row.models || "";
  form.enabled = row.enabled;
  dialogVisible.value = true;
}

async function handleSave() {
  saving.value = true;
  try {
    if (isEdit.value && editId.value) {
      await api.updateProvider(editId.value, { ...form });
      ElMessage.success("已更新");
    } else {
      await api.createProvider({ ...form });
      ElMessage.success("已创建");
    }
    dialogVisible.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  } finally {
    saving.value = false;
  }
}

async function handleDelete(row: Provider) {
  try {
    await ElMessageBox.confirm(`确定删除供应商「${row.name}」？`, "确认删除", { type: "warning" });
    await api.deleteProvider(row.id);
    ElMessage.success("已删除");
    await load();
  } catch { /* cancelled */ }
}

onMounted(load);
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add ArticleGeneratorAdm/src/views/ProvidersView.vue
git commit -m "feat: add Providers management page"
```

---

### Task 14: 前端 Scenario Configs 页面 + 路由注册

**Files:**
- Create: `ArticleGeneratorAdm/src/views/ScenarioConfigsView.vue`
- Modify: `ArticleGeneratorAdm/src/router/index.ts`

- [ ] **Step 1: 编写 ScenarioConfigsView.vue**

```vue
<template>
  <div class="scenario-configs-view">
    <div class="page-header">
      <h2>场景路由配置</h2>
      <el-button type="primary" @click="openCreate">新增配置</el-button>
    </div>

    <el-table :data="configs" stripe>
      <el-table-column prop="scenario" label="场景" width="140">
        <template #default="{ row }">
          <el-tag :type="scenarioType(row.scenario)">{{ scenarioLabel(row.scenario) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="供应商" width="120">
        <template #default="{ row }">{{ row.provider?.name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="model" label="模型" />
      <el-table-column label="优先级" width="80" prop="priority" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑配置' : '新增配置'" width="640px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="场景" required>
          <el-select v-model="form.scenario">
            <el-option value="distill" label="蒸馏" />
            <el-option value="generate" label="生成" />
            <el-option value="quality_review" label="质量评审" />
            <el-option value="compliance_review" label="合规评审" />
            <el-option value="refine" label="微调" />
          </el-select>
        </el-form-item>
        <el-form-item label="供应商" required>
          <el-select v-model="form.provider_id" placeholder="选择供应商">
            <el-option v-for="p in providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型" required>
          <el-input v-model="form.model" placeholder="claude-opus-4-7" />
        </el-form-item>
        <el-form-item label="System Prompt">
          <el-input v-model="form.system_prompt_template" type="textarea" :rows="5" placeholder="支持 {{变量}} 占位" />
        </el-form-item>
        <el-form-item label="参数">
          <el-input v-model="form.params" type="textarea" :rows="2" placeholder='{"temperature": 0.7, "max_tokens": 4096}' />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="0" :max="99" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">{{ isEdit ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api, ScenarioConfig, Provider } from "@/api/client";

const configs = ref<ScenarioConfig[]>([]);
const providers = ref<Provider[]>([]);
const dialogVisible = ref(false);
const isEdit = ref(false);
const saving = ref(false);
const editId = ref<number | null>(null);

const form = reactive({
  scenario: "generate",
  provider_id: 0,
  model: "",
  system_prompt_template: "",
  params: "",
  priority: 0,
  enabled: true,
});

const scenarioMap: Record<string, string> = {
  distill: "蒸馏", generate: "生成", quality_review: "质量评审",
  compliance_review: "合规评审", refine: "微调",
};

function scenarioLabel(s: string) { return scenarioMap[s] || s; }
function scenarioType(s: string) {
  const t: Record<string, string> = { distill: "warning", generate: "", quality_review: "success", compliance_review: "danger", refine: "info" };
  return t[s] || "";
}

function resetForm() {
  form.scenario = "generate";
  form.provider_id = 0;
  form.model = "";
  form.system_prompt_template = "";
  form.params = "";
  form.priority = 0;
  form.enabled = true;
  editId.value = null;
}

async function load() {
  const [c, p] = await Promise.all([api.getScenarioConfigs(), api.getProviders()]);
  configs.value = c.data;
  providers.value = p.data;
}

function openCreate() {
  resetForm();
  isEdit.value = false;
  dialogVisible.value = true;
}

function openEdit(row: ScenarioConfig) {
  resetForm();
  isEdit.value = true;
  editId.value = row.id;
  form.scenario = row.scenario;
  form.provider_id = row.provider_id;
  form.model = row.model;
  form.system_prompt_template = row.system_prompt_template || "";
  form.params = row.params || "";
  form.priority = row.priority;
  form.enabled = row.enabled;
  dialogVisible.value = true;
}

async function handleSave() {
  saving.value = true;
  try {
    if (isEdit.value && editId.value) {
      await api.updateScenarioConfig(editId.value, { ...form });
      ElMessage.success("已更新");
    } else {
      await api.createScenarioConfig({ ...form });
      ElMessage.success("已创建");
    }
    dialogVisible.value = false;
    await load();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || "操作失败");
  } finally {
    saving.value = false;
  }
}

async function handleDelete(row: ScenarioConfig) {
  try {
    await ElMessageBox.confirm(`确定删除场景「${scenarioLabel(row.scenario)}」的配置？`, "确认", { type: "warning" });
    await api.deleteScenarioConfig(row.id);
    ElMessage.success("已删除");
    await load();
  } catch { /* cancelled */ }
}

onMounted(load);
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
```

- [ ] **Step 2: 更新路由**

`ArticleGeneratorAdm/src/router/index.ts` 新增两条路由：

```typescript
{ path: "/providers", name: "Providers", component: () => import("@/views/ProvidersView.vue"), meta: { title: "API供应商" } },
{ path: "/scenario-configs", name: "ScenarioConfigs", component: () => import("@/views/ScenarioConfigsView.vue"), meta: { title: "场景配置" } },
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorAdm/src/views/ScenarioConfigsView.vue ArticleGeneratorAdm/src/router/index.ts
git commit -m "feat: add Scenario Configs page and register new routes"
```

---

### Task 15: 前端 Accounts 页面改造（参考文章 + 风格画像）

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/AccountsView.vue`

- [ ] **Step 1: 编写改造后的 AccountsView.vue**

在现有表格基础上，把"编辑账号"的弹窗改为带 tabs 的详情对话框，新增"参考文章"和"风格画像"两个 tab。由于完整代码较长，核心改造点如下：

```
原弹窗结构 → 改造为：
┌─ el-dialog ────────────────────────────────┐
│ el-tabs                                    │
│  ├─ el-tab-pane label="基本信息"            │
│  │   原有 form（platform, account_name）    │
│  │   移除 lora_path 字段                   │
│  ├─ el-tab-pane label="参考文章"            │
│  │   el-table: title, source_url, benchmark │
│  │   [添加文章] 按钮 → 弹出添加文章子对话框  │
│  │     输入：标题、正文（或粘贴链接自动解析） │
│  │     勾选"设为代表篇"                     │
│  └─ el-tab-pane label="风格画像"            │
│      状态标签 + 画像文本                     │
│      [蒸馏风格] 按钮（调用 api.triggerDistill）│
└─────────────────────────────────────────────┘
```

关键交互代码片段：

```typescript
// 参考文章相关
const refArticles = ref<ReferenceArticle[]>([]);

async function loadRefArticles(accountId: number) {
  const { data } = await api.getReferenceArticles(accountId);
  refArticles.value = data;
}

async function addRefArticle(accountId: number) {
  await api.createReferenceArticle(accountId, {
    title: refForm.title,
    content: refForm.content,
    source_url: refForm.source_url || undefined,
    is_benchmark: refForm.is_benchmark,
  });
  ElMessage.success("已添加");
  await loadRefArticles(accountId);
}

async function triggerDistill(accountId: number) {
  await api.triggerDistill(accountId);
  ElMessage.success("蒸馏任务已提交，请稍后刷新查看风格画像");
}
```

由于完整组件约 200 行，以上是核心交互代码。完整文件将在实施时编写。

- [ ] **Step 2: 更新左侧菜单（在 App.vue 中添加新菜单项）**

`ArticleGeneratorAdm/src/App.vue` 的 `<el-menu>` 中添加：

```html
<el-menu-item index="/providers">API 供应商</el-menu-item>
<el-menu-item index="/scenario-configs">场景配置</el-menu-item>
```

- [ ] **Step 3: Commit**

```bash
git add ArticleGeneratorAdm/src/views/AccountsView.vue ArticleGeneratorAdm/src/App.vue
git commit -m "feat: add reference articles, style profile, and distill to Accounts page"
```

---

### Task 16: 前端 Review 页面改造（评分 + 风险标签）

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/ReviewView.vue`

- [ ] **Step 1: 改造 ReviewView.vue**

在文章表格中新增两列和详情扩展：

```
表格新增列：
  - quality_score：质量评分（用 el-progress 或 el-tag 显示，绿色 80+、黄色 60-79、红色 <60）
  - compliance_score：合规评分（🟢安全 100、🟡低风险 60-99、🔴高风险 <60）

点击行展开详情区域增加：
  - 评审备注（review_notes 格式化展示）
  - 原有：全文预览、通过/拒绝/微调按钮
```

关键代码片段：

```html
<el-table-column label="质量" width="80">
  <template #default="{ row }">
    <el-tag v-if="row.quality_score" :type="scoreType(row.quality_score)" size="small">
      {{ row.quality_score }}
    </el-tag>
    <span v-else style="color:#999">-</span>
  </template>
</el-table-column>
<el-table-column label="合规" width="90">
  <template #default="{ row }">
    <el-tag v-if="row.compliance_score === 100" type="success" size="small">🟢 安全</el-tag>
    <el-tag v-else-if="row.compliance_score && row.compliance_score >= 60" type="warning" size="small">🟡 低风险</el-tag>
    <el-tag v-else-if="row.compliance_score" type="danger" size="small">🔴 高风险</el-tag>
    <span v-else style="color:#999">-</span>
  </template>
</el-table-column>
```

```typescript
function scoreType(s: number) {
  if (s >= 80) return "success";
  if (s >= 60) return "warning";
  return "danger";
}
```

- [ ] **Step 2: Commit**

```bash
git add ArticleGeneratorAdm/src/views/ReviewView.vue
git commit -m "feat: add quality and compliance scores to Review page"
```

---

### Task 17: 删除废弃代码 + 清理

**Files:**
- Delete: `LLMService/app/model_loader.py`
- Modify: `LLMService/app/generator.py` (已在 Task 6 处理)

- [ ] **Step 1: 删除 model_loader.py**

```bash
rm LLMService/app/model_loader.py
```

- [ ] **Step 2: 清理 llm_service 的 .env.example 中的废弃配置**

`LLMService/.env.example` 更新为：

```
# LLM 网关配置（Provider 和场景路由在管理后台配置）
BACKEND_API_URL=http://localhost:8000
```

- [ ] **Step 3: Commit**

```bash
git rm LLMService/app/model_loader.py
git add LLMService/.env.example
git commit -m "chore: remove deprecated model_loader.py and update env example"
```

---

## 验证 Checklist

实施完成后，运行以下验证：

- [ ] `cd ArticleGeneratorService && pytest tests/ -v` — 后端 API 测试全绿
- [ ] `cd LLMService && pytest tests/ -v` — 网关测试全绿
- [ ] `cd HotspotCrawler && pytest tests/ -v` — 热点抓取不受影响
- [ ] `cd ArticleGeneratorAdm && npx vitest run` — 前端测试通过
- [ ] 手动验证全流程：配置 Provider → 配置 Scenario → 添加参考文章 → 蒸馏 → 生成 → 评审显示评分
