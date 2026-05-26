"""
热点同步到后端测试用例
"""
from unittest.mock import patch, MagicMock

from crawler.sync_to_backend import sync_hotspots


def test_sync_hotspots_empty():
    """无热点时返回 created=0"""
    with patch("crawler.sync_to_backend.fetch_all_sources", return_value=[]):
        r = sync_hotspots(api_base="http://fake")
        assert r["created"] == 0
        assert r["total"] == 0


def test_sync_hotspots_success():
    """同步成功时返回后端响应"""
    items = [{"title": "T", "source": "S", "heat": 1, "summary": None, "url": ""}]
    with patch("crawler.sync_to_backend.fetch_all_sources", return_value=items):
        with patch("crawler.sync_to_backend.httpx") as m:
            resp = MagicMock()
            resp.json.return_value = {"created": 1, "total": 1}
            resp.raise_for_status = MagicMock()
            m.Client.return_value.__enter__.return_value.post.return_value = resp

            r = sync_hotspots(api_base="http://fake")
            assert r["created"] == 1
            assert r["total"] == 1
