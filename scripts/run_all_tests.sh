#!/bin/bash
# 运行各模块测试
set -e
cd "$(dirname "$0")/.."

echo "=== ArticleGeneratorService ==="
cd ArticleGeneratorService && python -m pytest tests/ -v --tb=short && cd ..

echo ""
echo "=== LLMService ==="
cd LLMService && python -m pytest tests/ -v --tb=short && cd ..

echo ""
echo "=== HotspotCrawler ==="
cd HotspotCrawler && python -m pytest tests/ -v --tb=short && cd ..

echo ""
echo "=== ArticleGeneratorAdm ==="
cd ArticleGeneratorAdm && npm run test && cd ..

echo ""
echo "=== 全部测试通过 ==="
