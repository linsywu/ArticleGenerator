#!/bin/bash
# ArticleGenerator 一键启动脚本
# 自动启动所有服务并打开浏览器

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Ctrl+C 时停止所有后台服务
cleanup() {
    echo ""
    echo "正在停止服务..."
    if [ -d "$ROOT/.cursor/logs" ]; then
        for f in "$ROOT/.cursor/logs/"*.pid; do
            [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null || true
        done
    fi
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "celery.*article_generator" 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

LOG_DIR="$ROOT/.cursor/logs"
mkdir -p "$LOG_DIR"

echo "=== ArticleGenerator 一键启动 ==="
echo "项目根目录: $ROOT"
echo ""

# 1. 检查/启动 Redis
echo "[1/7] 检查 Redis..."
if redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "  Redis 已运行"
elif command -v docker &>/dev/null; then
    echo "  使用 Docker 启动 Redis..."
    docker start redis-article 2>/dev/null || docker run -d --name redis-article -p 6379:6379 redis:7-alpine
    sleep 2
else
    echo "  错误: 未检测到 Redis。请先安装并启动 Redis，或安装 Docker 后重试。"
    exit 1
fi

# 2. 安装依赖（若需）
echo ""
echo "[2/7] 检查 Python 依赖..."
cd "$ROOT/LLMService" && pip install -q -r requirements.txt
cd "$ROOT/ArticleGeneratorService" && pip install -q -r requirements.txt
cd "$ROOT/HotspotCrawler" && pip install -q -r requirements.txt

# 3. 启动 LLM 服务（后台）
echo ""
echo "[3/7] 启动 LLM 服务 (端口 8001)..."
cd "$ROOT/LLMService"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 > "$LOG_DIR/llm.log" 2>&1 &
LLM_PID=$!
echo "  LLM PID: $LLM_PID"

# 4. 启动后端 API（后台）
echo ""
echo "[4/7] 启动后端 API (端口 8000)..."
cd "$ROOT/ArticleGeneratorService"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/api.log" 2>&1 &
API_PID=$!
echo "  API PID: $API_PID"

# 5. 启动 Celery Worker（后台）
echo ""
echo "[5/7] 启动 Celery Worker (auto-reload)..."
cd "$ROOT/ArticleGeneratorService"
nohup watchfiles --filter python "celery -A app.tasks:celery_app worker -l info" app/tasks.py > "$LOG_DIR/celery.log" 2>&1 &
CELERY_PID=$!
echo "  Celery PID: $CELERY_PID"

# 6. 等待 API 就绪后抓取热点
echo ""
echo "[6/7] 等待服务就绪并抓取热点..."
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/ >/dev/null 2>&1; then
        echo "  API 已就绪"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "  警告: API 启动超时，继续执行"
    fi
done
sleep 2
cd "$ROOT/HotspotCrawler"
python run_crawl.py 2>/dev/null || echo "  抓取热点跳过（可稍后手动执行）"

# 7. 安装前端依赖并启动
echo ""
echo "[7/7] 启动管理后台 (端口 5173)..."
cd "$ROOT/ArticleGeneratorAdm"
if [ ! -d node_modules ]; then
    npm install
fi

# 保存 PIDs 供停止脚本使用
echo "$LLM_PID" > "$LOG_DIR/llm.pid"
echo "$API_PID" > "$LOG_DIR/api.pid"
echo "$CELERY_PID" > "$LOG_DIR/celery.pid"

# 等待前端启动
npm run dev &
VITE_PID=$!
echo "$VITE_PID" > "$LOG_DIR/vite.pid"

# 等待 Vite 就绪
for i in {1..20}; do
    if curl -s http://localhost:5173/ >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
sleep 2

# 打开浏览器
echo ""
echo "=== 启动完成 ==="
echo "管理后台: http://localhost:5173"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

if command -v open &>/dev/null; then
    open "http://localhost:5173"
elif command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:5173"
else
    echo "请手动打开浏览器访问 http://localhost:5173"
fi

# 前台运行 Vite，便于查看日志；Ctrl+C 可停止
wait $VITE_PID 2>/dev/null || true
