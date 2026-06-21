## 1. MaterialsDirectionDialog 组件

- [ ] 1.1 创建 `ArticleGeneratorAdm/src/components/MaterialsDirectionDialog.vue`
- [ ] 1.2 实现弹窗基础结构：`el-dialog` + `modelValue`/`update:modelValue` props
- [ ] 1.3 实现方向生成 API 调用：复用 `api.generateDirections(accountId, title)` 
- [ ] 1.4 实现轮询逻辑：2s 间隔 × 30 次，复用 CreateView 的轮询模式
- [ ] 1.5 实现加载态：spinner + "正在生成创作方向..." 文案，按钮 disabled
- [ ] 1.6 实现方向卡片展示：选中高亮（border-color 变化），显示 id（A/B/C）+ title
- [ ] 1.7 实现失败态：错误提示 "生成失败，请重试" + 重试按钮
- [ ] 1.8 实现"去创作"按钮：关闭弹窗 → `router.push({ path: '/create', query: { idea, direction, account_id } })`

## 2. MaterialsView 集成

- [ ] 2.1 替换 `onCreateDirection` 占位 handler：改为打开 MaterialsDirectionDialog
- [ ] 2.2 在 MaterialsView 中引入并注册 MaterialsDirectionDialog 组件

## 3. CreateView query 参数预填

- [ ] 3.1 在 `CreateView.vue` 的 `onMounted` 中读取 `route.query.idea`，预填 Step 2 的 idea 输入框
- [ ] 3.2 方向生成完成后，检查 `route.query.direction`，匹配并预选对应方向
- [ ] 3.3 若 `route.query.account_id` 存在且与当前选中账号不同，自动切换账号

## 4. 验证

- [ ] 4.1 启动前后端服务，验证素材中心 → 点击"创作方向" → 生成成功 → 选择方向 → 跳转 CreateView
- [ ] 4.2 验证 CreateView 正确预填 idea 和预选 direction
- [ ] 4.3 验证生成失败时的重试流程
- [ ] 4.4 验证轮询超时（模拟慢响应）的错误提示
- [ ] 4.5 验证弹窗关闭后再次打开能重新生成
