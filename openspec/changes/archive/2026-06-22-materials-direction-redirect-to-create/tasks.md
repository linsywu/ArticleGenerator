## 1. 新增 material-summary 场景配置

- [ ] 1.1 `scripts/seed_providers.py` 加 material-summary 种子（system_prompt_template + params）
- [ ] 1.2 在 `/scenario-configs` 页面确认新场景出现

## 2. 后端：摘要生成 API + Celery 任务

- [ ] 2.1 `app/tasks.py` 新增 `trigger_material_summary` Celery 任务
- [ ] 2.2 `app/api/materials.py` 新增 `POST /api/materials/{id}/generate-summary`
- [ ] 2.3 任务解析 LLM 返回 → 存 `MpMaterial.summary`

## 3. 前端：MaterialsDirectionDialog 重写

- [ ] 3.1 弹窗三态：内容加载 → 摘要生成中（轮询）→ 就绪
- [ ] 3.2 就绪态：可编辑摘要 textarea + 账号选择列表
- [ ] 3.3 确认按钮：跳转 `/create?idea=<摘要>&account_id=<账号ID>`

## 4. CreateView 自动跳步

- [ ] 4.1 `onMounted` 中加：当 `route.query.account_id` 有效时，`currentStep = 1`

## 5. 验证

- [ ] 5.1 素材中心 → 创作方向 → AI 生成摘要 → 确认 → 选账号 → 跳转
- [ ] 5.2 摘要落库验证：素材列表中可看到摘要
- [ ] 5.3 CreateView 直接访问不受影响
