#!/usr/bin/env python3
"""
热点抓取入口：抓取并同步到后端
可配置定时任务（cron 或 Celery beat）每小时执行
"""
import os
import sys

# 将项目根目录加入 path，便于导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.sync_to_backend import sync_hotspots

if __name__ == "__main__":
    api_base = os.environ.get("API_BASE", "http://localhost:8000")
    sources = os.environ.get("CRAWL_SOURCES", "weibo,zhihu").split(",")
    result = sync_hotspots(api_base=api_base, sources=[s.strip() for s in sources if s.strip()])
    print(result)
