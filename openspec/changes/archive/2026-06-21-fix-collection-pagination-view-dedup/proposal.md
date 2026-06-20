## Why

用户报告了素材采集功能的 3 个问题：

1. **全量采集未翻页**：创建 `collect_mode="full"` 的采集任务后，素材中心只显示少量文章（实际只采了 10 篇）。根因是 `mp_client.py` 的 `_mode_count()` 没有 `"full"` 映射，默认回退到 10 篇。

2. **素材中心无法查看原文**：点击"查看"打开详情抽屉后，HTML 原文 Tab 显示空或无法正常渲染。需要排查 raw_html 存储→API 返回→前端渲染整个链路。

3. **采集去重确认**：经代码审查，采集去重已在 worker.py 中实现（original_url + content_hash 双重检查），无需修复。

## What Changes

- **修复** `mp_client.py` `_mode_count()` 添加 `"full"` 模式支持，使全量采集循环翻页直到 API 不再返回新数据
- **修复** 素材详情查看：排查并修复 raw_html 在前端抽屉中无法正确渲染原文的问题
- **确认** 去重逻辑已存在（URL + content hash），无需代码变更

## Capabilities

### New Capabilities

<!-- No new capabilities — bug fixes to existing collection pipeline -->

### Modified Capabilities

<!-- No spec-level requirement changes — implementation fixes only -->

## Impact

- **受影响文件（后端）**: `app/collector/mp_client.py`（_mode_count 添加 "full" 模式）
- **受影响文件（前端）**: `ArticleGeneratorAdm/src/views/MaterialsView.vue`（修复原文渲染）、可能 `app/api/materials.py`（如 API 返回有问题）
- **不涉及**: 数据库迁移、新增依赖、新增 API 路由
