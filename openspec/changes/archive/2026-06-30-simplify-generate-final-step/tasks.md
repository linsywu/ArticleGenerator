## 1. Frontend: CreateView.vue 步骤 6 改造

- [ ] 1.1 移除 `generatedArticle` 变量及相关展示模板（步骤 6 内容区）
- [ ] 1.2 修改 `startGenerate()`：移除轮询和 `api.getArticle()` 调用，提交任务成功后直接设置确认状态
- [ ] 1.3 步骤 6 模板改为确认信息："文章生产中，请前往任务中心查看" + "前往任务中心"按钮
- [ ] 1.4 移除 `watch(currentStep, ...)` 中步骤 6 的自动触发逻辑（`step === 5` watcher）

## 2. Verification

- [ ] 2.1 `npm run build` 构建通过
- [ ] 2.2 浏览器验证：走完创作流程 → 提交生成 → 确认页展示 → 跳转任务中心
