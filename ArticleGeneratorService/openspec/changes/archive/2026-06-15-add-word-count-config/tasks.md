## 1. DB 迁移

- [ ] 1.1 创建迁移脚本，accounts 表新增 `word_count_options` TEXT 和 `default_word_count` VARCHAR(20) 列
- [ ] 1.2 执行迁移

## 2. 后端 Model + Schema

- [ ] 2.1 `models.py` Account 模型新增两个字段
- [ ] 2.2 `schemas.py` AccountBase/AccountUpdate/AccountResponse 新增字段（word_count_options 存 JSON string，响应时解析为 list）
- [ ] 2.3 `schemas.py` DirectionsRequest 新增可选 `word_count: Optional[str]` 字段

## 3. 后端 API

- [ ] 3.1 `api/generate.py` directions 端点传递 `word_count` 到 Celery 任务
- [ ] 3.2 `tasks.py` trigger_direction_generation / trigger_generate / trigger_refine 接收 word_count 参数并注入提示词

## 4. 前端 Account 表单

- [ ] 4.1 `AccountsView.vue` 编辑表单新增加字数选项配置区（el-input 输入 JSON 或 key=value 逐行编辑）
- [ ] 4.2 新增默认字数下拉选择器（从 word_count_options 解析选项）

## 5. 前端 CreateView 字数选择器

- [ ] 5.1 `CreateView.vue` 步骤 2（输入想法）新增 el-select 字数选择器，从 account.word_count_options 读取选项
- [ ] 5.2 `generateDirections` 调用时传入 word_count
- [ ] 5.3 `startGenerate` 调用时传入 word_count

## 6. 提示词更新

- [ ] 6.1 在管理后台将 generate 场景 system_prompt_template 末尾添加 `{{word_count}}`
- [ ] 6.2 在管理后台将 refine 场景 system_prompt_template 末尾添加 `{{word_count}}`

## 7. 验证

- [ ] 7.1 验证：无 word_count 配置的账号仍正常生成（向后兼容）
- [ ] 7.2 验证：配置字数后，CreateView 可选字数并影响生成结果
