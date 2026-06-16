"""
TDD: 用户选择的标题应被持久化，而非从 LLM 输出中自动提取

Bug: 选择标题步骤中用户选的标题未被保存，
     文章列表展示的是 LLM 输出自动提取的标题
"""


def test_resolve_article_title_uses_passed_title_over_extracted():
    """
    resolve_article_title() 在传入了有效标题时应优先使用传入标题，
    而非从 LLM 内容中提取。
    """
    from app.tasks import resolve_article_title

    user_selected_title = "我的精选标题"
    llm_content = "# 其他标题\n\n这是文章正文内容。"

    result = resolve_article_title(
        content=llm_content,
        hotspot_title=user_selected_title,
    )

    assert result == user_selected_title, (
        f"应优先使用传入的标题 '{user_selected_title}'，但返回了 '{result}'"
    )


def test_resolve_article_title_falls_back_to_extraction_when_no_title_passed():
    """当没有传入标题时，应回退到从内容中提取标题"""
    from app.tasks import resolve_article_title

    result = resolve_article_title(
        content="# LLM 生成的标题\n\n正文内容。",
        hotspot_title=None,
    )

    assert result == "LLM 生成的标题"


def test_resolve_article_title_falls_back_to_extraction_when_title_empty():
    """当传入标题为空字符串时，应回退到从内容中提取标题"""
    from app.tasks import resolve_article_title

    result = resolve_article_title(
        content="无标记正文第一行\n第二行",
        hotspot_title="",
    )

    assert result == "无标记正文第一行"


def test_resolve_article_title_extracts_h1_first():
    """从内容提取标题时优先 # 标记"""
    from app.tasks import resolve_article_title

    assert resolve_article_title("# 一级标题\n\n正文", None) == "一级标题"


def test_resolve_article_title_extracts_h2_second():
    """从内容提取标题时 ## 标记次之"""
    from app.tasks import resolve_article_title

    assert resolve_article_title("## 二级标题\n\n正文", None) == "二级标题"


def test_resolve_article_title_extracts_first_line():
    """从内容提取标题时无标记取第一行非空文本"""
    from app.tasks import resolve_article_title

    assert resolve_article_title("第一行\n第二行", None) == "第一行"


def test_resolve_article_title_truncates_long_title():
    """传入标题过长时截断到 200 字符"""
    from app.tasks import resolve_article_title

    long_title = "这是" * 150  # 300 chars
    result = resolve_article_title(
        content="# 正文",
        hotspot_title=long_title,
    )

    assert len(result) <= 200
    assert result == long_title[:200]
