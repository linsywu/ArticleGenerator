-- 023_paragraph_level_review.sql
-- Change 2：段落级质量评审 + 模板升级

-- 新增段落级评审详情列
ALTER TABLE articles ADD COLUMN quality_review_detail TEXT;

-- 更新 quality_review 场景模板（JSON 输出 + max_tokens 4096）
UPDATE scenario_configs
SET system_prompt_template = '你是一位资深内容评审编辑。对以下文章做段落级质量评审，找出低质量段落并给出改进建议。\n\n## 评审步骤\n1. 按自然段落（空行分隔）从 1 开始编号（跳过标题行）。\n2. 逐段检查：是否套话堆砌？是否有信息增量？是否衔接自然？\n3. 对整体从四个维度打分（各25分）：原创性、逻辑性、可读性、信息密度。\n4. 仅列出 severity=high 或 medium 的问题段落（low 和正常段落不输出）。\n\n## 输出格式（严格 JSON，不要额外文字，不要 markdown 代码块标记）\n{\n  "overall_score": 85,\n  "dimensions": {"originality": 22, "logic": 21, "readability": 22, "info_density": 20},\n  "weak_paragraphs": [\n    {"index": 3, "severity": "high", "issue": "套话堆砌，信息密度低", "suggestion": "用具体数据替换「随着时代发展」类空话"}\n  ]\n}\n\n## 文章内容\n{{article_content}}',
    params = '{"max_tokens": 4096, "temperature": 0.3}',
    description = '⑥ 质量评审：段落级结构化 JSON（总分+四维+问题段落清单）'
WHERE scenario = 'quality_review';
