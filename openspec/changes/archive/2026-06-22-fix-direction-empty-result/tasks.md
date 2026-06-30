## 1. Backend: Celery task fix

- [ ] 1.1 `tasks.py` `trigger_direction_generation`：构建 `user_prompt` 变量（想法 + 字数 + 格式指令 + 可选风格提示）
- [ ] 1.2 `tasks.py` 备用解析器：正则增加中文格式支持（`方向[一二三四五六七八九十]`、`角度\d+`、`**[A-F]`）
- [ ] 1.3 `tasks.py` 最终兜底：所有解析失败时，将非空行（最多5行）作为方向返回

## 2. Config: 更新 direction 场景 prompt 模板

- [ ] 2.1 在 `/scenario-configs` 页面更新 `direction` 的 system_prompt_template，去掉对 `{{style_profile}}` 的硬依赖
- [ ] 2.2 验证：素材中心 → 文章 → 创作方向，多次点击确认不再出现空 directions

## 3. Verification

- [ ] 3.1 重启 Celery worker 使新代码生效
- [ ] 3.2 选一篇有摘要的素材，点"创作方向"，确认返回 3-5 个方向
- [ ] 3.3 选一篇只有标题的素材，点"创作方向"，确认返回方向（验证无内容时的兜底）
- [ ] 3.4 从创建页面选账号后生成方向，确认风格信息正常注入
