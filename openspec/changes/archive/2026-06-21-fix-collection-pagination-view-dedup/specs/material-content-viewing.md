# Material Content Viewing

## Requirement

素材中心"查看"功能必须能正常显示文章原文内容，包括已采集和新采集的素材。

## Acceptance Criteria

- [ ] 详情抽屉"原文 (HTML)" Tab 能渲染出文章正文内容（图片、段落格式可见）
- [ ] 不显示微信公众号后台 chrome（导航栏、侧边栏等）
- [ ] 对于 raw_html 为空的旧素材，显示"暂无原文内容"而非空白
- [ ] Markdown Tab 功能保持不变（点击加载 → 解析显示）

## Implementation

**Backend**: `app/api/materials.py`

在 `get_material` 响应中添加 `content_html` 字段，通过正则提取 `#js_content` div 内容：

```python
def _extract_article_content(html: str) -> str:
    if not html:
        return ""
    match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>', html, re.DOTALL)
    if match:
        content = match.group(1)
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        return content.strip()
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL)
    return cleaned
```

**Frontend**: `ArticleGeneratorAdm/src/views/MaterialsView.vue`

将 HTML Tab 的渲染源从 `currentMaterial.raw_html` 改为 `currentMaterial.content_html`（或 raw_html 的提取结果）。

**Schema**: `app/schemas.py`

`MpMaterialResponse` 添加 `content_html: Optional[str] = None` 字段。
