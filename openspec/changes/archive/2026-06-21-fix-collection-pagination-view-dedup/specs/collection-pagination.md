# Collection Pagination

## Requirement

全量采集模式（`collect_mode="full"`）必须翻页获取公众号的全部历史文章，直到 API 不再返回新数据为止。

## Acceptance Criteria

- [ ] `_mode_count("full")` 返回一个足够大的值（如 999999），使 `fetch_article_list` 的 while 循环持续翻页
- [ ] 翻页终止条件：当 `app_msg_list` 为空或小于 10 条时自动 break（现有逻辑已支持）
- [ ] `incremental`、`history_50`、`history_100`、`history_200` 模式行为不变
- [ ] 全量采集任务执行后，素材中心中该公众号的文章数量与公众号后台实际文章数量一致（允许 ±5 偏差）

## Implementation

**File**: `app/collector/mp_client.py`

在 `_mode_count()` 的 `mode_map` 中添加 `"full": 999999`。
