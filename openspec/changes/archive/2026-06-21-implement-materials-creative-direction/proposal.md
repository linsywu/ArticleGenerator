## Why

素材中心（MaterialsView）已展示已采集的文章素材，但缺少基于素材生成"创作方向"的能力。用户在素材列表中看到一篇感兴趣的文章后，无法直接在素材中心基于该素材生成写作方向——必须手动复制标题到文章创作向导（CreateView）中操作。补齐素材中心的创作方向入口，能让用户从"浏览素材 → 生成方向 → 创作文章"形成完整闭环。

## What Changes

- 素材中心表格操作列的"💡 创作方向"按钮从占位替换为功能弹窗
- 弹窗内调用已有的 `POST /generate/directions` API 生成 3-5 个写作方向
- 方向以卡片形式展示，用户可选择一个方向后跳转到文章创作向导（预填素材标题作为 idea）
- 复用已有的前端 API 层（`generateDirections` + `DirectionItem` 类型），不新增后端接口

## Capabilities

### New Capabilities
- `materials-direction-dialog`: 素材中心创作方向弹窗——基于选中素材的文章标题生成写作方向，支持轮询等待、方向选择、跳转文章创作向导

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- **前端**: `MaterialsView.vue`（替换占位 handler，新增弹窗组件或内联 dialog）
- **后端**: 无变更（复用 `POST /generate/directions` + `GET /generate/task/{task_id}/result`）
- **API**: 无新增接口
- **路由**: 无变更
