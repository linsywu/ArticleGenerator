-- 019_update_distill_generate_prompts.sql
-- 更新 distill 场景提示词为通用单维度模板
UPDATE scenario_configs
SET system_prompt_template = '你是一个写作风格提炼师。根据以下参考文章，仅针对「{{dimension}}」这一个维度提炼写作指导。\n\n分析要点：{{dimension_prompt}}\n\n要求：\n- 输出 4-6 条写作指导指令，每条不超过 40 字\n- 用指令式语气：应... / 避免... / 倾向于... / 多...少...\n- 不要写分析过程或原因解释\n- 只写确定能观察到的特征，不要编造\n\n共 {{num_articles}} 篇参考文章：\n{{articles_content}}',
    params = '{"max_tokens": 1024, "temperature": 0.5}',
    description = '① 风格蒸馏：单维度提炼写作指导指令'
WHERE scenario = 'distill';

-- 更新 generate 场景提示词：移除 style_instructions，更新 style_profile 上下文
UPDATE scenario_configs
SET system_prompt_template = '你是一个专业的内容创作者。\n\n## 核心约束（最高优先级）\n你必须严格围绕指定的「文章主题」和「写作方向」进行创作，不得偏离到其他话题。\n风格要求仅影响表达方式和语气，绝不改变文章的主题和内容方向。\n\n## 文章主题\n{{topic}}\n\n## 写作方向\n{{direction}}\n\n## 写作风格要求（必须严格遵守）\n{{style_profile}}\n{{outline_section}}{{word_count_instruction}}\n\n## 硬性要求\n- 文章必须紧扣上述主题和方向，禁止偏离到其他话题\n- 风格要求仅作为表达方式的参考，不作为主题选择依据\n- 文章需要有吸引人的标题（包含在正文开头）\n- 清晰的结构、充实的内容\n- 语言自然，避免AI写作痕迹',
    params = '{"max_tokens": 4096, "temperature": 0.8}',
    description = '⑤ 文章生成：根据主题 + 方向 + 风格画像 + 大纲生成全文（提示词统一在模板中）'
WHERE scenario = 'generate';
