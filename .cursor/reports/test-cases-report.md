# ArticleGenerator 测试用例报告

## 测试用例分布

| 模块 | 测试文件 | 用例数 | 说明 |
|------|----------|--------|------|
| ArticleGeneratorService | tests/test_api_*.py, test_root.py | 24 | 账号、热点、文章、生成、热点源、根路由 |
| LLMService | tests/test_api.py | 3 | 根路径、generate、refine 模拟模式 |
| HotspotCrawler | tests/test_sources.py, test_sync.py | 9 | parse_heat、fetch_hotlist、fetch_all_sources、sync_hotspots |
| ArticleGeneratorAdm | tests/api.test.ts, router.test.ts | 5 | API 方法、路由配置 |

## 运行方式

```bash
# 单模块
cd ArticleGeneratorService && python -m pytest tests/ -v
cd LLMService && python -m pytest tests/ -v
cd HotspotCrawler && python -m pytest tests/ -v
cd ArticleGeneratorAdm && npm run test

# 全部
./scripts/run_all_tests.sh
```

## 实施过程修改

为满足测试用例要求，对实现做了以下调整（未修改测试用例本身）：

1. **ArticleGeneratorService/app/api/hotspots.py**：批量创建时增加 `db.flush()`，使同批次去重逻辑正确生效
2. **ArticleGeneratorService/tests/conftest.py**：测试数据库隔离（临时文件 + 每用例前清空表）

## 测试结果

全部 41 个用例通过。
