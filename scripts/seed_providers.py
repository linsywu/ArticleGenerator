"""写入初始 Provider + ScenarioConfig 配置"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ArticleGeneratorService"))

from app.database import SessionLocal, engine, Base
from app.models import Provider, ScenarioConfig

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# 清除旧配置（幂等）
db.query(ScenarioConfig).delete()
db.query(Provider).delete()
db.commit()

# Provider: CrazyRouter
provider = Provider(
    name="CrazyRouter",
    base_url="https://crazyrouter.com/v1",
    api_key="sk-mhntt7cQ2icV1w6HZIr0EjRPp0v6WxAorYA609ZuIxvyamp5",
    models='["claude-sonnet-4-20250514", "deepseek-chat"]',
    enabled=1,
)
db.add(provider)
db.flush()

scenarios = [
    {
        "scenario": "generate",
        "model": "claude-sonnet-4-20250514",
        "system_prompt_template": (
            "你是一个专业的内容创作者。根据热点标题和风格要求，创作一篇高质量的文章。"
            "文章需要有吸引人的标题、清晰的结构、充实的内容。\n\n"
            "风格要求：{{style_profile}}\n\n"
            "热点标题：{{hotspot_title}}"
        ),
        "params": '{"max_tokens": 4096, "temperature": 0.8}',
        "priority": 10,
    },
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
    },
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
    },
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
    },
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
    },
]

for s in scenarios:
    db.add(ScenarioConfig(provider_id=provider.id, enabled=1, **s))

db.commit()
db.close()
print("Done: 1 provider + 5 scenario configs seeded.")
