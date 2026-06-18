<!-- 加载顺序：AI agent 应先加载本文件，再加载 ../CLAUDE.md 获取全局约束 -->
<!-- 本文件中的内容为 HotspotCrawler 独有；全局约定见 ../CLAUDE.md -->

# HotspotCrawler — 热点抓取服务

从微博/知乎/百度/抖音/B站等平台抓取热点，POST 到后端 `/api/hotspots/batch`。

## 常用命令

### 单次抓取

```bash
cd HotspotCrawler
pip install -r requirements.txt
python run_crawl.py
```

### 测试

```bash
cd HotspotCrawler && pytest tests/ -v
```

## 架构

### 抓取流程

1. 读取 `CRAWL_SOURCES` 环境变量（逗号分隔源列表）
2. 调用各平台免费聚合 API（基于 httpx）
3. 汇总结果，POST 到后端 `{API_BASE}/api/hotspots/batch`
4. 后端写入 `hotspots` 表（status=unselected）

## 配置

`.env` 文件（参考 `.env.example`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_BASE` | `http://localhost:8000` | 后端 API 地址 |
| `CRAWL_SOURCES` | `weibo,zhihu,baidu,douyin,bilibili` | 抓取源列表（逗号分隔） |

## 已知陷阱

### API 数据格式
POST 到 `/api/hotspots/batch` 的数据格式需与后端 Pydantic model 一致。新增字段时**必须同步更新**前后端 Schema。

### 抓取频率
免费聚合 API 有频率限制，避免在短时间内重复抓取同一平台。如遇限流，等待后重试。
