## 1. 后端 Schema 更新

- [ ] 1.1 `ArticleGeneratorService/app/schemas.py` — `DirectionItem` 新增 `angle`、`core_viewpoint`、`reader_gain`、`article_type`、`check` 五个 `Optional[str]` 字段，默认 `None`

## 2. 前端类型同步

- [ ] 2.1 `ArticleGeneratorAdm/src/api/types.ts` — `DirectionItem` 接口新增 `angle?: string`、`core_viewpoint?: string`、`reader_gain?: string`、`article_type?: string`、`check?: string`

## 3. 下游链路：title → core_viewpoint

- [ ] 3.1 `CreateView.vue` `generateOutline()` 中 `selectedDirection.value.title` → `selectedDirection.value.core_viewpoint || selectedDirection.value.title`（fallback 旧数据）
- [ ] 3.2 `CreateView.vue` `generateTitles()` 中同上替换
- [ ] 3.3 `CreateView.vue` `startGenerate()` 中同上替换
- [ ] 3.4 `CreateView.vue` 步骤 4 模板 `"方向：{{ selectedDirection?.title }}"` → `selectedDirection?.core_viewpoint`

## 4. 前端方向卡片重设计

- [ ] 4.1 `CreateView.vue` — 方向卡片模板改为层次布局（从上到下）：id + title（主行）→ core_viewpoint（灰色小字简介，line-clamp: 3）→ reader_gain → check → 底部 angle + article_type 彩色标签
- [ ] 4.2 `CreateView.vue` — 新增 `angleTagType()` 辅助函数，映射 angle 值到 Element Plus tag type 颜色
- [ ] 4.3 `CreateView.vue` — CSS 样式更新：`.direction-body` / `.direction-meta` / `.direction-check-text` 等新增样式类，`.direction-card` 改为 `align-items: flex-start`

## 5. 验证

- [ ] 5.1 启动后端 + 前端，走通"输入想法 → 生成方向 → 选择方向 → 大纲 → 标题 → 生成全文"完整流程
- [ ] 5.2 确认方向卡片展示全部 7 字段，卡片层次清晰
- [ ] 5.3 确认下游收到的是 `core_viewpoint`（80-150 字核心论点）而非短标题
- [ ] 5.4 模拟旧数据（无 `core_viewpoint`）测试 fallback 正常
