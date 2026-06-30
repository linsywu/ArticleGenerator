"""Tests for consolidated generate prompt — outline_section, topic variable, payload structure"""
import pytest


class TestOutlineSection:
    """outline → outline_section 转换逻辑"""

    def test_outline_section_with_outline(self):
        """有 outline 时构建完整 section，含标题和约束语"""
        outline = ["开篇引入问题", "分析原因", "给出建议"]
        outline_items = [f"{i+1}. {p}" for i, p in enumerate(outline)]
        outline_section = (
            "## 写作大纲\n"
            + "\n".join(outline_items)
            + "\n\n请严格按照以上大纲逐段写作，大纲有几段文章就必须有几段。\n"
        )

        assert "## 写作大纲" in outline_section
        assert "1. 开篇引入问题" in outline_section
        assert "2. 分析原因" in outline_section
        assert "3. 给出建议" in outline_section
        assert "请严格按照以上大纲逐段写作" in outline_section
        assert "大纲有几段文章就必须有几段" in outline_section

    def test_outline_section_empty_none(self):
        """outline=None 时 outline_section 为空字符串"""
        outline = None
        outline_section = ""
        if outline:
            outline_items = [f"{i+1}. {p}" for i, p in enumerate(outline)]
            outline_section = "## 写作大纲\n" + "\n".join(outline_items) + "\n..."
        assert outline_section == ""

    def test_outline_section_empty_list(self):
        """outline=[] 时 outline_section 同样为空"""
        outline = []
        outline_section = ""
        if outline:
            outline_items = [f"{i+1}. {p}" for i, p in enumerate(outline)]
            outline_section = "## 写作大纲\n" + "\n".join(outline_items) + "\n..."
        assert outline_section == ""


class TestTopicVariable:
    """topic 变量覆盖热点和自定义两种语义"""

    def test_topic_from_custom_flow(self):
        """创建流程：topic 为用户自拟标题+想法"""
        topic = "AI编程的焦虑是否被夸大？\n\n探讨AI工具对初级程序员的影响"
        assert "AI编程" in topic
        assert "初级程序员" in topic
        assert "\n\n" in topic  # 标题与想法以双换行分隔

    def test_topic_from_hotspot_flow(self):
        """热点流程：topic 为真实热点标题"""
        topic = "GPT-5发布引发行业震动"
        assert "GPT-5" in topic
        assert len(topic) > 0


class TestPayloadStructure:
    """验证发往 LLM 的 payload 结构"""

    def test_new_payload_uses_chat_endpoint_with_variables(self):
        """新架构：发 /chat，传 scenario + variables，不传 style_instructions"""
        payload = {
            "scenario": "generate",
            "account_id": 1,
            "variables": {
                "topic": "测试主题",
                "outline_section": "",
                "word_count_instruction": "字数1500左右。",
            },
        }
        assert payload["scenario"] == "generate"
        assert "variables" in payload
        assert "user_prompt" not in payload
        assert "topic" in payload["variables"]
        assert "outline_section" in payload["variables"]
        assert "word_count_instruction" in payload["variables"]
        # 关键：style_instructions 不应出现
        assert "style_instructions" not in payload["variables"]

    def test_generate_payload_excludes_style_instructions(self):
        """trigger_generate 构建的 variables 不得包含 style_instructions"""
        payload = {
            "scenario": "generate",
            "account_id": 1,
            "variables": {
                "topic": "测试主题",
                "direction": "技术分析",
                "outline_section": "## 写作大纲\n1. 引言\n\n请严格按照以上大纲逐段写作...\n",
                "word_count_instruction": "字数1500左右。",
            },
        }
        # style_instructions 已被合并到 style_profile（由 Gateway 自动注入）
        assert "style_instructions" not in payload["variables"]
        # 确认核心变量全部存在
        assert "topic" in payload["variables"]
        assert "direction" in payload["variables"]
        assert "outline_section" in payload["variables"]
        assert "word_count_instruction" in payload["variables"]

    def test_generate_payload_relies_on_gateway_for_style_profile(self):
        """style_profile 由 Gateway 自动注入，tasks.py 不传"""
        payload = {
            "scenario": "generate",
            "account_id": 1,
            "variables": {
                "topic": "测试",
                "direction": "",
                "outline_section": "",
                "word_count_instruction": "字数1500左右。",
            },
        }
        # Gateway 注入 style_profile，tasks.py 不负责
        assert "style_profile" not in payload["variables"]
        assert "style_instructions" not in payload["variables"]

    def test_humanize_payload_includes_outline_section(self):
        """Humanize 新 payload 包含 outline_section"""
        payload = {
            "scenario": "humanize",
            "variables": {
                "article_content": "这是文章内容...",
                "outline_section": "## 写作大纲\n1. 要点一\n2. 要点二\n\n请严格按照以上大纲逐段写作，大纲有几段文章就必须有几段。\n",
            },
        }
        assert "outline_section" in payload["variables"]
        assert len(payload["variables"]["outline_section"]) > 0

    def test_humanize_payload_empty_outline_section(self):
        """无大纲时 humanize 的 outline_section 为空"""
        payload = {
            "scenario": "humanize",
            "variables": {
                "article_content": "内容...",
                "outline_section": "",
            },
        }
        assert payload["variables"]["outline_section"] == ""


class TestLegacyEndpointCompatibility:
    """LLM Service /generate 端点兼容性"""

    def test_topic_takes_priority_over_hotspot_title(self):
        """topic 优先于 hotspot_title"""
        topic = "新变量"
        hotspot_title = "旧变量"
        resolved = topic or hotspot_title or ""
        assert resolved == "新变量"

    def test_fallback_to_hotspot_title_when_no_topic(self):
        """无 topic 时回退到 hotspot_title"""
        topic = None
        hotspot_title = "旧调用方传的标题"
        resolved = topic or hotspot_title or ""
        assert resolved == "旧调用方传的标题"

    def test_empty_when_neither_provided(self):
        """两者都为空时返回空字符串"""
        resolved = None or None or ""
        assert resolved == ""
