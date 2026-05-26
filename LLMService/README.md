# LLMService

模型推理服务，提供 `/generate` 和 `/refine` 接口。

## 模拟模式（默认）

无需 GPU，直接返回模拟内容，用于开发联调：

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## 真实模式

需配置 GPU、模型路径，并设置 `MOCK_MODE=False`：

1. 复制 `.env.example` 为 `.env`，设置：
   - `MOCK_MODE=false`
   - `MODEL_PATH=/path/to/chatglm3-6b`（或 Qwen-7B 等）
   - `LORA_PATH=/path/to/lora`（可选，账号未配置时使用）

2. 安装依赖（含 torch、transformers、peft）：
   ```bash
   pip install -r requirements.txt
   ```
   若需 CUDA，可单独安装：`pip install torch --index-url https://download.pytorch.org/whl/cu118`

3. 启动服务：
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```

4. 账号的 LoRA 路径：在管理后台「账号管理」中为账号配置 `lora_path`，生成时会自动传递并加载对应 LoRA。
