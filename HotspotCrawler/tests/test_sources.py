"""
热点源 parse_heat、fetch_hotlist 测试用例
"""
import pytest
from unittest.mock import patch, MagicMock

from crawler.sources import parse_heat, fetch_hotlist, fetch_all_sources


def test_parse_heat_wan():
    """解析「111.7万」为 1117000"""
    assert parse_heat("111.7万") == 1117000


def test_parse_heat_yi():
    """解析「1.5亿」为 150000000"""
    assert parse_heat("1.5亿") == 150000000


def test_parse_heat_empty():
    """空字符串返回 0"""
    assert parse_heat("") == 0


def test_parse_heat_pure_number():
    """纯数字返回整型"""
    assert parse_heat("12345") == 12345


def test_fetch_hotlist_success():
    """API 返回成功时解析正确"""
    mock_data = {
        "success": True,
        "data": [
            {"title": "热点A", "hot": "111.7万", "url": "http://a.com"},
            {"title": "热点B", "hot": "50万", "url": "http://b.com"},
        ],
    }
    with patch("crawler.sources.httpx") as m:
        resp = MagicMock()
        resp.json.return_value = mock_data
        resp.raise_for_status = MagicMock()
        m.Client.return_value.__enter__.return_value.get.return_value = resp

        result = fetch_hotlist("weibo")
        assert len(result) == 2
        assert result[0]["title"] == "热点A"
        assert result[0]["heat"] == 1117000
        assert result[0]["source"] == "微博热搜"


def test_fetch_hotlist_empty():
    """API 返回空 data 时返回 []"""
    with patch("crawler.sources.httpx") as m:
        resp = MagicMock()
        resp.json.return_value = {"success": True, "data": []}
        resp.raise_for_status = MagicMock()
        m.Client.return_value.__enter__.return_value.get.return_value = resp

        result = fetch_hotlist("weibo")
        assert result == []


def test_fetch_all_sources_dedupe():
    """多源抓取去重"""
    with patch("crawler.sources.fetch_hotlist") as m:
        m.side_effect = [
            [{"title": "相同", "source": "微博热搜", "heat": 100, "summary": None, "url": ""}],
            [{"title": "相同", "source": "微博热搜", "heat": 200, "summary": None, "url": ""}],
        ]
        result = fetch_all_sources(["weibo", "zhihu"])
        assert len(result) == 1