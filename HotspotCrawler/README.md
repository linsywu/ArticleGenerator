# HotspotCrawler

热点抓取模块，从微博、知乎、百度等平台获取热榜，并同步到后端。

## 运行

```bash
pip install -r requirements.txt
python run_crawl.py
```

## 环境变量

- `API_BASE`: 后端 API 地址，默认 http://localhost:8000
- `CRAWL_SOURCES`: 抓取源，逗号分隔，如 weibo,zhihu,baidu

## 定时任务

可使用 cron 每小时执行：
```
0 * * * * cd /path/to/HotspotCrawler && python run_crawl.py
```
