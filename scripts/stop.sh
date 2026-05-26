#!/bin/bash
# 停止 ArticleGenerator 所有服务

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT/.cursor/logs"

echo "=== 停止 ArticleGenerator 服务 ==="

for name in vite celery api llm; do
    pidfile="$LOG_DIR/${name}.pid"
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null && echo "  已停止 $name (PID $pid)"
        fi
        rm -f "$pidfile"
    fi
done

# 额外清理可能残留的进程
pkill -f "uvicorn app.main:app.*8000" 2>/dev/null && echo "  已停止 API"
pkill -f "uvicorn app.main:app.*8001" 2>/dev/null && echo "  已停止 LLM"
pkill -f "celery.*article_generator" 2>/dev/null && echo "  已停止 Celery"
pkill -f "vite.*5173" 2>/dev/null && echo "  已停止 Vite"

echo "完成"
