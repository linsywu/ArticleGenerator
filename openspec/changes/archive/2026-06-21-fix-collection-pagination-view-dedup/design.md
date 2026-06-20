## Design

### 1. Full Collection Pagination Fix

**Root Cause**: `mp_client.py:_mode_count()` maps `history_50/100/200` and `incremental` modes to fixed article counts. `"full"` is not in the map, so `mode_map.get("full", 10)` returns 10 — the incremental default.

```python
# Current (broken)
@staticmethod
def _mode_count(mode: str) -> int:
    mode_map = {"history_50": 50, "history_100": 100, "history_200": 200, "incremental": 10}
    return mode_map.get(mode, 10)
```

**Fix**: Since `fetch_article_list()` already has a proper termination condition (`if len(app_msg_list) < 10: break`), the simplest fix is to assign a large sentinel count for `"full"` mode. The while loop `while begin < count` will paginate until the API returns fewer than 10 results (or 0), then break.

```python
# Fixed
@staticmethod
def _mode_count(mode: str) -> int:
    mode_map = {"full": 999999, "history_50": 50, "history_100": 100, "history_200": 200, "incremental": 10}
    return mode_map.get(mode, 10)
```

**Why 999999**: WeChat MP API typically has far fewer articles per account. The loop's `if len(app_msg_list) < 10: break` on line 96 acts as the real terminator. 999999 is a safe upper bound that will never be reached before the API exhausts results.

**No changes needed** to `fetch_article_list()`, worker.py, or the CollectTask model — the existing loop logic handles pagination correctly for any count value.

### 2. Material Content Viewing Fix

**Investigation**:

The data flow is:
1. Worker collects: `raw_html = client.fetch_article_html(art["link"])` → stored in `MpMaterial.raw_html`
2. API returns: `get_material()` includes `"raw_html": material.raw_html` in response dict
3. Frontend renders: `<div class="html-preview" v-html="currentMaterial.raw_html || '(无内容)'" />`

The pipeline appears intact at first glance. Possible failure points:

**Hypothesis A — raw_html contains WeChat page chrome, not just article**: `fetch_article_html()` fetches the full article page URL. WeChat MP article pages contain the article content inside `#js_content` div within a full page wrapper. The `v-html` renders this full page HTML (with all its scripts, styles, navigation) which may display as broken/unreadable in the drawer.

**Hypothesis B — raw_html is empty for pre-existing materials**: Materials collected before the `raw_html` field was added would have NULL `raw_html`, showing "(无内容)".

**Hypothesis C — Script/style interference**: The `v-html` directive renders HTML but does NOT execute scripts. WeChat article pages contain scripts that may interfere with rendering or leave the page in a broken state visually.

**Recommended Fix** (Hypothesis A + C):

Add server-side HTML extraction in `fetch_article_html()` or create a new method that extracts the article content from the WeChat page wrapper, returning only the `<div id="js_content">` body content. This:

1. Removes WeChat chrome (navigation, header, footer, sidebars)
2. Removes `<script>` and `<style>` tags that can't execute anyway
3. Preserves images and formatting
4. Makes the content actually readable in `v-html`

```python
def fetch_article_html(self, url: str) -> str:
    """Fetch and extract article content from WeChat MP page"""
    self.limiter.wait()
    resp = self.session.get(url, timeout=30)
    resp.encoding = "utf-8"
    html = resp.text
    
    # Extract article content from WeChat MP wrapper
    import re
    match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*<script', html, re.DOTALL)
    if match:
        return f'<div id="js_content">{match.group(1)}</div>'
    
    # Fallback: return full HTML
    return html
```

Wait — this would affect the stored `raw_html` for all new collections. But existing materials already have full page HTML stored. We need a migration approach.

**Better approach — fix at display time**:

Instead of changing what's stored, extract the article content in the `/materials/{id}` API response. This is backward-compatible with existing data and doesn't require re-collection.

Add a helper in `mp_client.py` (or materials.py) that extracts `#js_content` from stored raw_html:

```python
# In materials.py or as a static method on MpClient
def _extract_article_content(html: str) -> str:
    """Extract article body from WeChat MP page HTML"""
    if not html:
        return ""
    match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>', html, re.DOTALL)
    if match:
        content = match.group(1)
        # Remove inline scripts
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        # Keep images and formatting
        return content.strip()
    # Fallback: strip scripts and styles, return cleaned HTML
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL)
    return cleaned
```

The API response for `get_material()` then includes both:
- `raw_html`: the original stored HTML (for debugging)
- `content_html`: extracted article content (for display)

And the frontend renders `content_html` instead of `raw_html` in the "原文" tab.

### 3. Deduplication — Confirmed Working

Worker.py `_collect_from_account()` implements two-layer dedup:

```python
# Layer 1: URL-based (before fetching HTML — saves bandwidth)
existing = db.query(MpMaterial).filter(MpMaterial.original_url == art["link"]).first()
if existing:
    continue

# Layer 2: Content hash-based (after fetching HTML — catches mirror/repost)
hash_exists = db.query(MpMaterial).filter(MpMaterial.content_hash == content_hash).first()
if hash_exists:
    continue
```

No changes needed. Result reported to user as "已确认有去重".
