-- 024_add_refine_paragraph_scenario.sql
-- Change 3：新增段落级微调场景（单段输入/输出，后端切片拼接）

INSERT INTO scenario_configs (scenario, model, system_prompt_template, params, priority, enabled, provider_id, description)
VALUES (
    'refine-paragraph',
    'gpt-5',
    '你是专业内容编辑。仅改写下方【待改写段落】，输出改写后的单段文本（不要输出其他段落、不要解释、不要 markdown 标记）。\n\n## 写作风格要求\n{{style_profile}}\n\n## 该段落的问题\n{{issue}}\n\n## 改进建议\n{{suggestion}}\n\n## 用户补充要求\n{{keywords}}\n\n## 待改写段落\n{{paragraph_text}}',
    '{"max_tokens": 2048, "temperature": 0.4}',
    10,
    1,
    1,
    '⑦ 段落级微调：单段改写（后端切片逐段调用，拼接回填）'
);
