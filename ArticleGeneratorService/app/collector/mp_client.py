"""
微信公众号 API 客户端
"""
import time
import random
import hashlib
import re
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime


class RateLimiter:
    def __init__(self, min_interval: float = 15.0, jitter: float = 5.0):
        self.min_interval = min_interval
        self.jitter = jitter
        self._last_request = 0.0

    def wait(self):
        elapsed = time.monotonic() - self._last_request
        wait_time = self.min_interval + random.uniform(0, self.jitter)
        if elapsed < wait_time:
            time.sleep(wait_time - elapsed)
        self._last_request = time.monotonic()


class MpClient:
    BASE_URL = "https://mp.weixin.qq.com"

    def __init__(self, token: str, cookie: str, min_interval: float = 15.0):
        self.token = token
        self.cookie = cookie
        self.limiter = RateLimiter(min_interval=min_interval)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Cookie": cookie,
            "Referer": f"{self.BASE_URL}/cgi-bin/appmsg",
        })

    def _get(self, path: str, params: dict) -> requests.Response:
        self.limiter.wait()
        url = f"{self.BASE_URL}{path}"
        params["token"] = self.token
        params["lang"] = "zh_CN"
        params["f"] = "json"
        return self.session.get(url, params=params, timeout=30)

    def search_account(self, name: str) -> Optional[Dict[str, Any]]:
        resp = self._get("/cgi-bin/searchbiz", {
            "action": "search_biz", "query": name,
            "begin": "0", "count": "1",
        })
        data = resp.json()
        biz_list = data.get("list", [])
        if not biz_list:
            return None
        item = biz_list[0]
        return {
            "name": item.get("nickname", name),
            "alias": item.get("alias", ""),
            "fakeid": str(item.get("fakeid", "")),
            "biz": item.get("alias", ""),
            "avatar": item.get("round_head_img", ""),
            "description": item.get("signature", ""),
        }

    def fetch_article_list(self, fakeid: str, mode: str = "incremental",
                           date_start: Optional[str] = None, date_end: Optional[str] = None
                           ) -> List[Dict[str, Any]]:
        articles = []
        count = self._mode_count(mode)
        begin = 0
        while begin < count:
            params = {
                "action": "list_ex", "type": "9", "query": "",
                "fakeid": fakeid, "begin": str(begin), "count": "10",
            }
            resp = self._get("/cgi-bin/appmsg", params)
            data = resp.json()
            app_msg_list = data.get("app_msg_list", [])
            if not app_msg_list:
                break
            for msg in app_msg_list:
                articles.append({
                    "title": msg.get("title", ""),
                    "link": msg.get("link", ""),
                    "aid": str(msg.get("aid", "")),
                    "create_time": msg.get("create_time", 0),
                    "cover": msg.get("cover", ""),
                    "digest": msg.get("digest", ""),
                })
            if len(app_msg_list) < 10:
                break
            begin += 10
        return articles

    def fetch_article_html(self, url: str) -> str:
        self.limiter.wait()
        resp = self.session.get(url, timeout=30)
        resp.encoding = "utf-8"
        return resp.text

    def extract_metadata(self, html: str) -> Dict[str, Any]:
        result = {"title": "", "author": "", "published_at": None}
        title_match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
        if title_match:
            result["title"] = title_match.group(1)
        author_match = re.search(r'<meta[^>]+property="og:article:author"[^>]+content="([^"]+)"', html)
        if author_match:
            result["author"] = author_match.group(1)
        time_match = re.search(r'<meta[^>]+property="og:article:publish_time"[^>]+content="([^"]+)"', html)
        if time_match:
            try:
                result["published_at"] = datetime.fromtimestamp(int(time_match.group(1)))
            except (ValueError, TypeError):
                pass
        return result

    @staticmethod
    def content_hash(html: str) -> str:
        return hashlib.sha256(html.encode("utf-8")).hexdigest()

    @staticmethod
    def estimate_word_count(html: str) -> int:
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\s+', '', text)
        return len(text)

    @staticmethod
    def _mode_count(mode: str) -> int:
        mode_map = {"history_50": 50, "history_100": 100, "history_200": 200, "incremental": 10}
        return mode_map.get(mode, 10)

    def check_health(self) -> bool:
        try:
            resp = self._get("/cgi-bin/searchbiz", {
                "action": "search_biz", "query": "人民日报",
                "begin": "0", "count": "1",
            })
            data = resp.json()
            return data.get("base_resp", {}).get("ret") == 0
        except Exception:
            return False
