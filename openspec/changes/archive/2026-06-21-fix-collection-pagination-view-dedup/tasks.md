# Tasks: Fix Collection Pagination, Content Viewing & Dedup

## 1. Fix full collection pagination

- [ ] Add `"full": 999999` to `_mode_count()` mode_map in `app/collector/mp_client.py`
- [ ] Verify existing modes (`incremental`, `history_50/100/200`) unchanged

**Files**: `app/collector/mp_client.py`

## 2. Fix material content viewing

- [ ] Add `_extract_article_content()` helper to `app/api/materials.py` (extract `#js_content` div from WeChat page HTML)
- [ ] Add `content_html` field to `MpMaterialResponse` in `app/schemas.py`
- [ ] Return `content_html` in `get_material` API response
- [ ] Update `MaterialsView.vue` HTML tab to render `content_html` instead of `raw_html`
- [ ] Handle edge case: show "暂无原文内容" when both `content_html` and `raw_html` are empty

**Files**: `app/api/materials.py`, `app/schemas.py`, `ArticleGeneratorAdm/src/views/MaterialsView.vue`

## 3. Verify deduplication (read-only)

- [ ] Confirm `_collect_from_account()` in `app/collector/worker.py` has URL-based dedup (line 122-128)
- [ ] Confirm content-hash-based dedup (line 131-133)
- [ ] Report result to user — no code changes needed

**Files**: None (verification only)

## 4. End-to-end verification

- [ ] Start backend + frontend dev servers
- [ ] Create and execute a "full" mode collect task for a test account
- [ ] Verify materials list shows all articles (compare count with WeChat MP backend)
- [ ] Click "查看" on a material → verify "原文" tab shows readable article content
- [ ] Run `verifier-unit` + `verifier-e2e`
