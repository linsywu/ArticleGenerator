## Context

用户手动修改了 direction 提示词，LLM 现在输出 7 字段结构：

```json
[{
  "id": "A",
  "title": "用户浏览时看到的一句话标题（20~30字）",
  "angle": "切入方式（反常识/社会观察/心理机制/利益驱动/故事切入等）",
  "core_viewpoint": "80~150字核心论点，用于后续AI生成大纲",
  "reader_gain": "一句话说明读者读完最大的认知收获",
  "article_type": "现象解读型 / 方法论分享型 / ...",
  "check": "好奇：xx钩子；增量：xx；共鸣：xx"
}]
```

关键区别：`title` 是给用户看的短标题（20-30字），`core_viewpoint` 是给后续 AI 步骤用的完整论点（80-150字）。当前代码把 `title` 传入了 `generateOutline`、`generateTitles`、`startGenerate`，导致下游生成的提示词只收到一个短标题而非完整的核心论点，影响大纲和文章质量。

数据流：`LLM → tasks.py JSON解析 → Celery result → getTaskResult API → 前端 directions.value`

## Goals / Non-Goals

**Goals:**
- 后端 `DirectionItem` schema 支持全部 7 个字段（5 个新增，均为 Optional）
- 前端方向卡片重设计：标题 + 核心论点简介 + reader_gain + check + 底部标签
- 下游 4 处 `selectedDirection.value.title` → `selectedDirection.value.core_viewpoint`
- 旧格式方向数据（仅 `id`/`title`）不报错，`v-if` 优雅降级

**Non-Goals:**
- 不修改 direction 提示词本身
- 不修改 tasks.py 解析逻辑（已透传所有 JSON 字段）
- 不修改后端 `/generate/directions` API 接口

## Decisions

1. **全部字段 Optional** — 向后兼容旧数据、手动输入、不同版本的提示词输出
2. **卡片信息层次（从上到下）** — id 标签 + title（主行 bold）→ core_viewpoint（灰色简介）→ reader_gain（小字）→ check（最小字）→ 底部 angle + article_type 彩色标签
3. **下游传递 core_viewpoint** — 在所有调用 `generateOutline`/`generateTitles`/`startGenerate` 的地方，以及步骤 4 模板展示中，将 `selectedDirection.value.title` 替换为 `selectedDirection.value.core_viewpoint`
4. **angle 标签颜色映射** — 反常识=danger, 社会观察=warning, 心理机制=info, 利益驱动=success, 故事切入=""

## Risks / Trade-offs

- `core_viewpoint` 为 None（旧数据）时下游传空字符串 → 兜底：`selectedDirection.value.core_viewpoint || selectedDirection.value.title`，确保旧方向仍可用
- core_viewpoint 80-150 字较长 → 卡片中截断或用 `line-clamp: 3` 限制行数
