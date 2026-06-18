<!-- 加载顺序：AI agent 应先加载本文件，再加载 ../CLAUDE.md 获取全局约束 -->
<!-- 本文件中的内容为 LLMService 独有；全局约定见 ../CLAUDE.md -->

# LLMService — LLM 推理服务

基于 FastAPI + transformers + peft 的模型推理服务，提供 `/generate` 和 `/refine` 端点。支持 `MOCK_MODE` 模拟和真实 LoRA 推理。

## 常用命令

### 启动

```bash
cd LLMService
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 测试

```bash
cd LLMService && pytest tests/ -v
```

## 架构

### API 端点

| 端点 | 用途 |
|------|------|
| `POST /generate` | 根据热点标题 + 账号风格生成文章 |
| `POST /refine` | 根据评审意见微调已有文章 |

### 模拟模式

默认 `MOCK_MODE=true`，无需 GPU，返回模拟生成内容。设为 `false` 后加载真实模型 + LoRA adapter。

## 配置

`.env` 文件（参考 `.env.example`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MOCK_MODE` | `true` | 模拟模式开关 |
| `MODEL_PATH` | — | 基础模型路径（MOCK_MODE=false 时必填） |
| `LORA_PATH` | — | LoRA adapter 路径（MOCK_MODE=false 时必填） |

## 已知陷阱

### Provider Adapter 注册
新增 LLM Provider 后必须：
1. 在 `LLMService/app/adapters/__init__.py` 中导入 adapter 模块
2. 通过 `register("provider名称")` 注册
3. OpenAI 兼容厂商（如 CrazyRouter）注册为 `OpenAIAdapter` 别名

### CrazyRouter 模型
- **可用模型**：`deepseek-v4-pro`（中文创作首选）、`deepseek-chat`（评审任务）
- **不可用**：`claude-sonnet-4-20250514`（该名称在 CrazyRouter 上无效）
- 场景→模型映射在 `scenario_configs` 表中，通过管理后台「场景配置」管理

### Generate Prompt 分层架构
generate 场景采用 4 层结构：
1. 角色定义
2. 硬约束/禁用词（总的来说、综上所述、首先其次最后、换言之、从某种程度上、随着、在当前）
3. `{{style_profile}}` 占位 — 账号风格画像
4. 任务指令 + `{{hotspot_title}}` — 实际生成请求

修改 Prompt 后需通过 Celery 重新生成验证效果。

### JSON 参数解析
LLM 网关请求参数需为合法 JSON。遗留端点使用 Pydantic model 校验，新增端点需同样定义 Schema。
