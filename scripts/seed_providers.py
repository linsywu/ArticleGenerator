"""写入初始 Provider + ScenarioConfig 配置（幂等 UPSERT）"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ArticleGeneratorService"))

from app.database import SessionLocal, engine, Base
from app.models import Provider, ScenarioConfig

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ---------------------------------------------------------------------------
# Provider: CrazyRouter  ——  UPSERT 模式
# ---------------------------------------------------------------------------
provider_data = dict(
    name="CrazyRouter",
    base_url="https://crazyrouter.com/v1",
    api_key="sk-mhntt7cQ2icV1w6HZIr0EjRPp0v6WxAorYA609ZuIxvyamp5",
    models='["claude-sonnet-4-20250514", "deepseek-chat"]',
    enabled=1,
)

existing_provider = db.query(Provider).filter(Provider.name == "CrazyRouter").first()
if existing_provider:
    # 保留既有的 api_key，更新可能发生变化的字段
    existing_provider.base_url = provider_data["base_url"]
    existing_provider.models = provider_data["models"]
    existing_provider.enabled = provider_data["enabled"]
    provider = existing_provider
    print(f"Updated existing provider: {provider.name} (id={provider.id})")
else:
    provider = Provider(**provider_data)
    db.add(provider)
    print(f"Created new provider: {provider.name}")

db.flush()

# ---------------------------------------------------------------------------
# 9 个 ScenarioConfig ——  UPSERT 模式
# ---------------------------------------------------------------------------
scenarios = [
    # ── ① 风格蒸馏 ──────────────────────────────────────────────────────────
    {
        "scenario": "distill",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "分析以下参考文章，提炼出账号的写作风格画像。\n\n"
            "分析维度：\n"
            "1. 语气特点（正式/口语化/幽默/严肃等）\n"
            "2. 用词习惯（常用词汇、专业术语偏好）\n"
            "3. 句式特点（长短句偏好、修辞手法）\n"
            "4. 开头方式（常见开篇模式）\n"
            "5. 结尾方式（常见收尾模式）\n"
            "6. 段落结构（段落长度、逻辑组织方式）\n"
            "7. 目标读者画像\n\n"
            "共 {num_articles} 篇参考文章：\n{{articles_content}}"
        ),
        "params": '{"max_tokens": 2048, "temperature": 0.5}',
        "priority": 10,
        "description": "① 风格蒸馏：分析参考文章，提取7维度结构化风格画像",
        "sort_order": 1,
    },
    # ── ⓪ 素材摘要 ──────────────────────────────────────────────────────────
    {
        "scenario": "material-summary",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个专业的内容编辑。请将以下文章内容总结为简洁的摘要，"
            "保留核心观点和关键信息，150-300字。\n\n"
            "标题：{{title}}\n\n"
            "文章内容：\n{{content}}"
        ),
        "params": '{"max_tokens": 1024, "temperature": 0.5}',
        "priority": 10,
        "description": "⓪ 素材摘要：根据素材内容生成简洁摘要",
        "sort_order": 0,
    },
    # ── ② 方向生成 ──────────────────────────────────────────────────────────
    {
        "scenario": "direction",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个专业的内容策划。根据给定的想法，生成3-5个不同的写作方向。\n\n"
            "每个方向是一个不同的切入角度，用一句话描述。\n\n"
            "{{style_profile}}"
            "想法：{{idea}}\n\n"
            "请以JSON数组格式输出：[{\"id\": \"A\", \"title\": \"切入角度\"}, {\"id\": \"B\", \"title\": \"切入角度\"}, ...]"
        ),
        "params": '{"max_tokens": 2048, "temperature": 0.9}',
        "priority": 10,
        "description": "② 方向生成：根据想法和账号风格，生成3-5个切入角度",
        "sort_order": 2,
    },
    # ── ③ 大纲生成 ──────────────────────────────────────────────────────────
    {
        "scenario": "outline",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个专业的内容策划。根据想法、写作方向和账号风格，生成5-8个要点的文章大纲。\n\n"
            "每个要点用一句话概括核心内容。\n\n"
            "风格要求：{{style_profile}}\n"
            "想法：{{idea}}\n"
            "方向：{{direction}}"
        ),
        "params": '{"max_tokens": 2048, "temperature": 0.8}',
        "priority": 10,
        "description": "③ 大纲生成：根据想法+方向+风格，生成5-8个要点大纲",
        "sort_order": 3,
    },
    # ── ④ 标题生成 ──────────────────────────────────────────────────────────
    {
        "scenario": "title",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个专业的内容编辑。根据想法、写作方向和大纲，生成3-5个吸引人的文章标题。\n\n"
            "标题要求：\n"
            "1. 简洁有力，15字以内为佳\n"
            "2. 能准确传达文章核心观点\n"
            "3. 符合账号的写作风格\n"
            "4. 有一定吸引力但不标题党\n\n"
            "风格要求：{{style_profile}}\n"
            "想法：{{idea}}\n"
            "方向：{{direction}}\n"
            "大纲：{{outline}}"
        ),
        "params": '{"max_tokens": 1024, "temperature": 0.9}',
        "priority": 10,
        "description": "④ 标题生成：根据想法+方向+大纲，生成3-5个候选标题",
        "sort_order": 4,
    },
    # ── ⑤ 文章生成 ──────────────────────────────────────────────────────────
    {
        "scenario": "generate",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个专业的内容创作者。\n\n"
            "## 任务\n"
            "根据以下信息创作一篇高质量的文章。\n\n"
            "## 文章主题\n"
            "{{topic}}\n\n"
            "## 风格画像\n"
            "{{style_profile}}\n\n"
            "{{style_instructions}}"
            "{{outline_section}}"
            "{{word_count_instruction}}\n\n"
            "## 要求\n"
            "- 文章需要有吸引人的标题（包含在正文开头）\n"
            "- 清晰的结构、充实的内容\n"
            "- 语言自然，避免AI写作痕迹"
        ),
        "params": '{"max_tokens": 4096, "temperature": 0.8}',
        "priority": 10,
        "description": "⑤ 文章生成：根据主题 + 风格画像 + 大纲生成全文（提示词统一在模板中）",
        "sort_order": 5,
    },
    # ── ⑥ 去AI味 ────────────────────────────────────────────────────────────
    {
        "scenario": "humanize",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个资深编辑，擅长让AI生成的文章读起来像真人写的。\n\n"
            "{{outline_section}}"
            "请对以下文章进行「去AI味」处理：\n"
            "1. 打破过于工整的对称结构\n"
            "2. 加入自然的语气变化和口语化表达\n"
            "3. 减少「首先/其次/最后/总而言之」等套路连接词\n"
            "4. 适当加入个人化的观点和感受\n"
            "5. 段落长短错落，避免每段都是3-4句\n"
            "6. 如果原文有大纲结构要求，重写时保持段落结构不变\n\n"
            "文章内容：\n{{article_content}}"
        ),
        "params": '{"max_tokens": 4096, "temperature": 0.7}',
        "priority": 5,
        "description": "⑥ 去AI味：重写文章，消除AI写作痕迹，增加人味儿（感知大纲结构）",
        "sort_order": 6,
    },
    # ── ⑦ 质量评审 ──────────────────────────────────────────────────────────
    {
        "scenario": "quality_review",
        "model": "deepseek-chat",
        "system_prompt_template": (
            "请对以下文章进行质量评审，给出0-100的分数。\n\n"
            "评审维度（各25分）：\n"
            "1. 原创性：内容是否新颖，避免套话\n"
            "2. 逻辑性：论证是否清晰，结构是否合理\n"
            "3. 可读性：语言是否流畅，段落是否易读\n"
            "4. 信息密度：是否提供了有价值的信息\n\n"
            "输出格式：先逐项打分并说明理由，最后一行给出总分（如：总分：85）\n\n"
            "文章内容：\n{{article_content}}"
        ),
        "params": '{"max_tokens": 1024, "temperature": 0.3}',
        "priority": 5,
        "description": "⑦ 质量评审：从原创性、逻辑、可读性、信息密度四个维度评分",
        "sort_order": 7,
    },
    # ── ⑧ 合规评审 ──────────────────────────────────────────────────────────
    {
        "scenario": "compliance_review",
        "model": "deepseek-chat",
        "system_prompt_template": (
            "请对以下文章进行合规检查，判断是否包含违规内容。\n\n"
            "检查项：\n"
            "1. 政治敏感内容\n"
            "2. 色情低俗内容\n"
            "3. 暴力恐怖内容\n"
            "4. 虚假信息\n"
            "5. 侵权内容\n\n"
            "如果内容完全安全合规，只回复 safe。"
            "如果有风险，说明具体问题并给出0-100的合规分数。\n\n"
            "文章内容：\n{{article_content}}"
        ),
        "params": '{"max_tokens": 1024, "temperature": 0.1}',
        "priority": 5,
        "description": "⑧ 合规评审：检查政治敏感、色情、暴力、虚假信息、侵权风险",
        "sort_order": 8,
    },
    # ── ⑨ 微调重写 ──────────────────────────────────────────────────────────
    {
        "scenario": "refine",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个专业的内容编辑。根据修改关键词对原文进行重写优化，"
            "保持文章核心信息不变，但按照关键词方向调整风格、语气或侧重点。\n\n"
            "原文：{{article_content}}\n\n"
            "修改关键词：{{keywords}}"
        ),
        "params": '{"max_tokens": 4096, "temperature": 0.7}',
        "priority": 10,
        "description": "⑨ 微调重写：根据修改关键词调整文章风格/语气/侧重点",
        "sort_order": 9,
    },
]

for s in scenarios:
    existing = db.query(ScenarioConfig).filter(ScenarioConfig.scenario == s["scenario"]).first()
    if existing:
        # 只更新元数据字段，不覆盖用户已调试好的 prompt/model/params/priority
        existing.description = s.get("description")
        existing.sort_order = s.get("sort_order", 0)
        existing.provider_id = provider.id
        existing.enabled = 1
        print(f"Updated scenario (metadata only): {s['scenario']}")
    else:
        db.add(ScenarioConfig(provider_id=provider.id, enabled=1, **s))
        print(f"Created scenario: {s['scenario']}")

db.commit()
db.close()
print("Done: 1 provider + 9 scenario configs seeded (UPSERT).")
