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
    # ── ① 风格蒸馏 Stage 1：证据提取 ──────────────────────────────────────────
    {
        "scenario": "distill-extract",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一位资深的写作风格分析师。通读以下参考文章，提炼这位作者**独有**的写作风格特征。\n\n"
            "## 工作步骤\n\n"
            "### 第一步：定位作者类型\n"
            "判断这位作者属于什么类型/垂类（情感两性、科技评论、财经分析、文学散文、生活方式、知识科普等），"
            "以及该类型的「主流写法」是什么样。后续所有「独特性」判断都以此为基准。\n\n"
            "### 第二步：提取标志性特征\n"
            "在该类型内，找出这位作者**区别于主流写法**的标志性特征。"
            "只提取这位作者确实有、而同类型普通写作者没有的特征——不要给通用写作建议。\n\n"
            "## 硬性要求（违反则失败）\n"
            "1. **每条特征必须附原文逐字引用**（用「」标出原句/原词）。没有原文佐证的特征不要写。\n"
            "2. **不要写通用建议**。「应多用短句」「应结构清晰」这类对任何作者都成立的话，一律删除。\n"
            "3. **维度自定**：不要套用固定维度。这位作者最值得提炼的方面是什么，你就提炼什么。\n"
            "4. 宁可少而准（5-8 条带引证的特征），不要多而泛。\n\n"
            "## few-shot 对比\n\n"
            "❌ 泛化（错误）：「应优先使用短句，增强冲击力」——这是通用建议，任何作者都成立\n"
            "✅ 具体（正确）：「设问式开头：「你有没有发现，越是懂事的女人，越没人疼？」"
            "——几乎每篇用反问设问开篇制造代入感」\n\n"
            "## 输出格式\n\n"
            "作者类型：<判断的类型> · <一句话主流写法画像>\n\n"
            "标志性特征：\n"
            "1. <特征名>：「<原文引用>」—— <如何体现该特征，1 句话>\n"
            "2. ...\n"
            "（5-8 条）\n\n"
            "共 {{num_articles}} 篇参考文章：\n{{articles_content}}"
        ),
        "params": '{"max_tokens": 2048, "temperature": 0.2}',
        "priority": 10,
        "description": "① 蒸馏 Stage1 证据提取：定位作者类型+提取带引证的标志性特征",
        "sort_order": 1,
    },
    # ── ① 风格蒸馏 Stage 2：凝练指南 ──────────────────────────────────────────
    {
        "scenario": "distill-synthesize",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一位写作教练。下面是一位作者的标志性特征清单（含原文引证）。"
            "请把它凝练成一份**可直接指导模仿**的《写作风格指南》。\n\n"
            "## 特征清单\n{{features}}\n\n"
            "## 要求\n\n"
            "1. **保留具体范例**：指南必须包含——标志性开头范例（1-2 例，带原句）、"
            "标志性结尾范例（1-2 例，带原句）、高频标志词清单（具体词）、禁忌词/禁忌处理清单。\n"
            "2. **指令必须由范例推出**：每条写作指令都应能从上面的特征清单找到依据，不要凭空增加。\n"
            "3. **用第二人称指令式**，把范例嵌进指令：「开头常用设问引入，如『你有没有发现...』」。\n"
            "4. **连贯成文**：不是罗列，而是一份读起来连贯的风格说明，让另一个写作者读完就能上手模仿。\n\n"
            "## 输出\n\n"
            "一份 600-900 字的《写作风格指南》，段落自定，"
            "但必须包含开头/结尾/标志词/禁忌这几类具体样板。"
        ),
        "params": '{"max_tokens": 2048, "temperature": 0.5}',
        "priority": 10,
        "description": "① 蒸馏 Stage2 凝练指南：特征清单→含范例的写作风格指南",
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
            "## 核心约束（最高优先级）\n"
            "你必须严格围绕指定的「文章主题」和「写作方向」进行创作，不得偏离到其他话题。\n"
            "风格要求仅影响表达方式和语气，绝不改变文章的主题和内容方向。\n\n"
            "## 文章主题\n"
            "{{topic}}\n\n"
            "## 写作方向\n"
            "{{direction}}\n\n"
            "## 写作风格要求（必须严格遵守）\n"
            "{{style_profile}}\n"
            "{{outline_section}}"
            "{{word_count_instruction}}\n\n"
            "## 硬性要求\n"
            "- 文章必须紧扣上述主题和方向，禁止偏离到其他话题\n"
            "- 风格要求仅作为表达方式的参考，不作为主题选择依据\n"
            "- 文章需要有吸引人的标题（包含在正文开头）\n"
            "- 清晰的结构、充实的内容\n"
            "- 语言自然，避免AI写作痕迹"
        ),
        "params": '{"max_tokens": 4096, "temperature": 0.8}',
        "priority": 10,
        "description": "⑤ 文章生成：根据主题 + 方向 + 风格画像 + 大纲生成全文（提示词统一在模板中）",
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

# 删除旧的 distill 场景（已被 distill-extract + distill-synthesize 替代）
old_distill = db.query(ScenarioConfig).filter(ScenarioConfig.scenario == "distill").first()
if old_distill:
    db.delete(old_distill)
    print("Deleted legacy scenario: distill (replaced by distill-extract + distill-synthesize)")

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
print("Done: 1 provider + scenario configs seeded (UPSERT).")
