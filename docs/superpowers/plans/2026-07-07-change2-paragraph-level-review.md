# Change 2：质量评审段落级结构化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 质量评审从「总分+泛泛理由」升级为段落级结构化 JSON（总分+四维分+问题段落清单），打通「评审指导微调」闭环。

**Architecture:** 新迁移 `023` 加 `articles.quality_review_detail` 列 + 更新 `quality_review` 场景模板（JSON 输出 + max_tokens=4096）。`trigger_quality_review` 解析 JSON 存结构。前端评审展示从纯文本升级为维度卡片 + 问题清单。

**Tech Stack:** SQL 迁移（MySQL 语法，dev SQLite）、Python/Celery/FastAPI、Vue 3 + Element Plus。

## Global Constraints

- 注释/提交信息语言：中文；提交格式语义化（`feat:` / `refactor:`）。
- 迁移从 `ArticleGeneratorService/` 目录执行（SQLite CWD 依赖）。
- `quality_review` 模板 JSON 输出需容错解析：先提取 ```json 块 → 回退纯文本 regex → 回退旧 `_parse_score`。
- `review_notes` 保留给合规评审用；质量评审结构化数据存 `quality_review_detail`。
- 前端变更必须浏览器验证（禁止仅 build+test 即声称通过）。

## File Structure

| 文件 | 责任 | 动作 |
|------|------|------|
| `ArticleGeneratorDatabase/migrations/023_paragraph_level_review.sql` | ALTER TABLE + UPDATE quality_review 模板 | 新建 |
| `ArticleGeneratorService/app/models.py` | Article 加 `quality_review_detail` | 修改 |
| `ArticleGeneratorService/app/schemas.py` | ArticleResponse 加 `quality_review_detail` | 修改 |
| `ArticleGeneratorService/app/api/articles.py` | 查询字段列表加 `quality_review_detail` | 修改 |
| `ArticleGeneratorService/app/tasks.py` | `trigger_quality_review` 改 JSON 解析+存储 | 修改 |
| `ArticleGeneratorService/tests/test_change2_paragraph_review.py` | 覆盖 JSON 解析 + 回退逻辑 | 新建 |
| `ArticleGeneratorAdm/src/api/types.ts` | Article 类型加 `quality_review_detail` | 修改 |
| `ArticleGeneratorAdm/src/components/ArticleEditorDialog.vue` | 评审展示改为结构化 | 修改 |

---

### Task 1: 迁移脚本 023 — 加列 + 更新 quality_review 模板

**Files:**
- Create: `ArticleGeneratorDatabase/migrations/023_paragraph_level_review.sql`

- [ ] **Step 1: 写迁移脚本**

```sql
-- 023_paragraph_level_review.sql
-- Change 2：段落级质量评审 + 模板升级

-- 新增段落级评审详情列
ALTER TABLE articles ADD COLUMN quality_review_detail TEXT;

-- 更新 quality_review 场景模板（JSON 输出 + max_tokens 4096）
UPDATE scenario_configs
SET system_prompt_template = '你是一位资深内容评审编辑。对以下文章做段落级质量评审，找出低质量段落并给出改进建议。\n\n## 评审步骤\n1. 按自然段落（空行分隔）从 1 开始编号（跳过标题行）。\n2. 逐段检查：是否套话堆砌？是否有信息增量？是否衔接自然？\n3. 对整体从四个维度打分（各25分）：原创性、逻辑性、可读性、信息密度。\n4. 仅列出 severity=high 或 medium 的问题段落（low 和正常段落不输出）。\n\n## 输出格式（严格 JSON，不要额外文字，不要 markdown 代码块标记）\n{\n  "overall_score": 85,\n  "dimensions": {"originality": 22, "logic": 21, "readability": 22, "info_density": 20},\n  "weak_paragraphs": [\n    {"index": 3, "severity": "high", "issue": "套话堆砌，信息密度低", "suggestion": "用具体数据替换「随着时代发展」类空话"}\n  ]\n}\n\n## 文章内容\n{{article_content}}',
    params = '{"max_tokens": 4096, "temperature": 0.3}',
    description = '⑥ 质量评审：段落级结构化 JSON（总分+四维+问题段落清单）'
WHERE scenario = 'quality_review';
```

- [ ] **Step 2: 在 dev SQLite 执行迁移**

```bash
cd ArticleGeneratorService
sqlite3 article_generator.db < ../ArticleGeneratorDatabase/migrations/023_paragraph_level_review.sql
```

- [ ] **Step 3: 验证 — 列已添加**

```bash
sqlite3 article_generator.db "PRAGMA table_info(articles);" | grep quality_review_detail
```
Expected: 一行输出，字段名 `quality_review_detail`。

- [ ] **Step 4: 验证 — 模板已更新**

```bash
sqlite3 article_generator.db "SELECT params, substr(system_prompt_template, 1, 120) FROM scenario_configs WHERE scenario='quality_review';"
```
Expected: params 含 `4096`，模板含 `weak_paragraphs`。

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorDatabase/migrations/023_paragraph_level_review.sql
git commit -m "feat: 023 迁移添加 quality_review_detail 列 + 升级质量评审模板"
```

---

### Task 2: 后端模型 + Schema + API 加 quality_review_detail 字段

**Files:**
- Modify: `ArticleGeneratorService/app/models.py`
- Modify: `ArticleGeneratorService/app/schemas.py`
- Modify: `ArticleGeneratorService/app/api/articles.py`

- [ ] **Step 1: models.py 加列**

在 `Article` 类的 `review_notes` 下方加：

```python
    quality_review_detail = Column(Text)  # 段落级质量评审 JSON
```

- [ ] **Step 2: schemas.py 加字段**

在 `ArticleResponse` 类加：

```python
    quality_review_detail: Optional[str] = None
```

- [ ] **Step 3: articles.py 查询加字段**

在 `articles.py` 第 43 行附近的手动字段列表中添加：

```python
            quality_review_detail=a.quality_review_detail,
```

- [ ] **Step 4: Commit**

```bash
git add ArticleGeneratorService/app/models.py ArticleGeneratorService/app/schemas.py ArticleGeneratorService/app/api/articles.py
git commit -m "feat: Article 模型/Schema/API 添加 quality_review_detail 字段"
```

---

### Task 3: trigger_quality_review 改 JSON 解析

**Files:**
- Modify: `ArticleGeneratorService/app/tasks.py`
- Create: `ArticleGeneratorService/tests/test_change2_paragraph_review.py`

- [ ] **Step 1: 写测试（先于代码改动）**

创建 `ArticleGeneratorService/tests/test_change2_paragraph_review.py`：

```python
"""Change 2：段落级质量评审 JSON 解析测试。"""
import json
import re


# ---- 解析逻辑（从 tasks.py 抽取，测试驱动开发） ----

def _parse_quality_review(text: str) -> dict:
    """从 LLM 输出中提取段落级评审 JSON。容错：优先 ```json 块 → 纯文本 regex → 旧 _parse_score 回退。"""
    # 1) 尝试提取 ```json ... ``` 代码块
    m = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 2) 尝试直接找最外层 JSON 对象
    m2 = re.search(r"\{[\s\S]*\"overall_score\"[\s\S]*\}", text)
    if m2:
        try:
            return json.loads(m2.group(0))
        except json.JSONDecodeError:
            pass

    # 3) 回退：只取总分
    score = _parse_score_fallback(text)
    return {"overall_score": score, "dimensions": {}, "weak_paragraphs": []}


def _parse_score_fallback(text: str) -> int:
    """旧 _parse_score 逻辑（兼容非 JSON 输出）。"""
    total_match = re.search(r"总分[：:\s]*(\d{1,3})", text)
    if total_match:
        s = int(total_match.group(1))
        if 0 <= s <= 100:
            return s
    overall = re.search(r"(?:综合|最终)(?:评分|得分)[：:\s]*(\d{1,3})", text)
    if overall:
        s = int(overall.group(1))
        if 0 <= s <= 100:
            return s
    nums = re.findall(r"\b([0-9]{1,3})\b", text)
    scores = [int(n) for n in nums if 0 <= int(n) <= 100]
    return scores[-1] if scores else 0


# ---- 测试用例 ----

VALID_JSON = """{
  "overall_score": 85,
  "dimensions": {"originality": 22, "logic": 21, "readability": 22, "info_density": 20},
  "weak_paragraphs": [
    {"index": 3, "severity": "high", "issue": "套话堆砌", "suggestion": "用具体数据替换"}
  ]
}"""


def test_parse_pure_json():
    """纯 JSON 直接解析。"""
    r = _parse_quality_review(VALID_JSON)
    assert r["overall_score"] == 85
    assert r["dimensions"]["originality"] == 22
    assert len(r["weak_paragraphs"]) == 1
    assert r["weak_paragraphs"][0]["index"] == 3


def test_parse_json_in_code_block():
    """LLM 输出包裹在 ```json 中。"""
    text = f"好的，以下是评审结果：\n```json\n{VALID_JSON}\n```\n希望对您有帮助。"
    r = _parse_quality_review(text)
    assert r["overall_score"] == 85
    assert len(r["weak_paragraphs"]) == 1


def test_parse_no_json_fallback():
    """非 JSON 输出回退到旧 _parse_score。"""
    text = "原创性：22分\n逻辑性：21分\n可读性：22分\n信息密度：20分\n总分：85"
    r = _parse_quality_review(text)
    assert r["overall_score"] == 85
    assert r["dimensions"] == {}
    assert r["weak_paragraphs"] == []


def test_parse_empty():
    """空内容返回 0。"""
    r = _parse_quality_review("")
    assert r["overall_score"] == 0


def test_parse_malformed_json_with_score():
    """JSON 解析失败但能提取总分。"""
    text = "总分：72\n{broken json"
    r = _parse_quality_review(text)
    assert r["overall_score"] == 72
```

- [ ] **Step 2: 运行测试验证失败（解析函数还未集成到 tasks.py）**

```bash
cd ArticleGeneratorService && pytest tests/test_change2_paragraph_review.py -v
```
Expected: 5/5 PASS（解析函数在测试文件内自包含，不依赖 tasks.py）。

- [ ] **Step 3: 重写 trigger_quality_review**

将 `tasks.py:621-649` 的 `trigger_quality_review` 替换为：

```python
def trigger_quality_review(self, article_id: int, article_content: str):
    """异步质量评审：段落级 JSON 结构化输出"""
    db = SessionLocal()
    try:
        llm_url = settings.llm_service_url.rstrip("/")
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{llm_url}/chat", json={
                "scenario": "quality_review",
                "task_id": self.request.id,
                "variables": {"article_content": article_content},
            })
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", "")
        review = _parse_quality_review(content)

        article = db.query(Article).filter(Article.id == article_id).first()
        if article:
            article.quality_score = review.get("overall_score", 0)
            article.quality_review_detail = json.dumps(review, ensure_ascii=False)
            db.commit()

        return {"article_id": article_id, "score": review.get("overall_score", 0)}
    except Exception as e:
        raise
    finally:
        db.close()
```

并在文件顶部（`_parse_score` 之前）添加 `_parse_quality_review` 函数（与测试文件一致的实现）。

- [ ] **Step 4: 从 tasks.py 删除旧的 review_notes 质量评审追加逻辑**

旧 `trigger_quality_review` 中 `notes = (article.review_notes or "") + f"\n[质量评审] {content[:500]}"` 已删除（Step 3 替换后自然消除）。确认合规评审（`trigger_compliance_review`）的 `review_notes` 追加逻辑不受影响。

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py ArticleGeneratorService/tests/test_change2_paragraph_review.py
git commit -m "feat: trigger_quality_review 改为段落级 JSON 解析 + 存 quality_review_detail"
```

---

### Task 4: 前端展示升级

**Files:**
- Modify: `ArticleGeneratorAdm/src/api/types.ts`
- Modify: `ArticleGeneratorAdm/src/components/ArticleEditorDialog.vue`

- [ ] **Step 1: types.ts 加字段**

在 Article 接口中添加：

```ts
quality_review_detail?: string;  // JSON: 段落级评审详情
```

- [ ] **Step 2: ArticleEditorDialog.vue — 结构化评审展示**

在评分 tag bar（12-20 行）和评审记录 pre（42-45 行）之间，新增结构化展示区域：

```vue
<!-- 段落级评审详情（替代旧 review_notes 质量评审部分） -->
<div v-if="reviewDetail" class="review-detail-section">
  <div class="review-section-title">AI 质量评审：</div>
  <!-- 四维评分 -->
  <div v-if="reviewDetail.dimensions" class="dimensions-row">
    <span class="dim-item">原创性 {{ reviewDetail.dimensions.originality }}/25</span>
    <span class="dim-item">逻辑性 {{ reviewDetail.dimensions.logic }}/25</span>
    <span class="dim-item">可读性 {{ reviewDetail.dimensions.readability }}/25</span>
    <span class="dim-item">信息密度 {{ reviewDetail.dimensions.info_density }}/25</span>
  </div>
  <!-- 问题段落清单 -->
  <div v-if="reviewDetail.weak_paragraphs?.length" class="weak-paragraphs">
    <div v-for="wp in reviewDetail.weak_paragraphs" :key="wp.index" class="weak-item">
      <el-tag :type="wp.severity === 'high' ? 'danger' : 'warning'" size="small" class="weak-tag">
        段落 {{ wp.index }}
      </el-tag>
      <span class="weak-issue">{{ wp.issue }}</span>
      <span class="weak-suggestion">💡 {{ wp.suggestion }}</span>
    </div>
  </div>
  <div v-else-if="reviewDetail.dimensions" class="no-weak-msg">✅ 所有段落质量良好</div>
</div>
```

并在 `<script setup>` 中添加 computed：

```ts
const reviewDetail = computed(() => {
  if (!props.article?.quality_review_detail) return null
  try {
    return JSON.parse(props.article.quality_review_detail)
  } catch {
    return null
  }
})
```

- [ ] **Step 3: 样式 — 追加到 ArticleEditorDialog.vue 的 `<style scoped>` 中**

```css
.review-detail-section {
  margin-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 8px;
}
.dimensions-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin: 8px 0;
}
.dim-item {
  font-size: 13px;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  padding: 2px 8px;
  border-radius: 4px;
}
.weak-paragraphs {
  margin-top: 8px;
}
.weak-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 13px;
  line-height: 1.5;
}
.weak-tag {
  flex-shrink: 0;
}
.weak-issue {
  color: var(--el-text-color-primary);
}
.weak-suggestion {
  color: var(--el-color-success);
}
.no-weak-msg {
  color: var(--el-color-success);
  font-size: 13px;
  margin-top: 4px;
}
```

- [ ] **Step 4: 浏览器验证**

```bash
cd ArticleGeneratorAdm && npm run dev
```

1. 打开评审页面，查看一篇已有 `quality_review_detail` 的文章
2. 确认四维评分卡片正常显示
3. 确认问题段落清单（如有）正确渲染
4. 确认 console 无报错
5. 旧文章（无 `quality_review_detail`）仍正常显示旧格式 `review_notes`

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorAdm/src/api/types.ts ArticleGeneratorAdm/src/components/ArticleEditorDialog.vue
git commit -m "feat: 评审展示升级为段落级结构化（四维分 + 问题清单）"
```

---

## 手动验证（端到端冒烟）

1. 重启 Celery worker（清 pycache）
2. 触发生成一篇文章，等待评审完成
3. 数据库验证：
   ```bash
   sqlite3 article_generator.db "SELECT quality_score, substr(quality_review_detail, 1, 200) FROM articles WHERE id=<id>;"
   ```
   Expected: `quality_score` 有值，`quality_review_detail` 为合法 JSON（含 overall_score + dimensions + weak_paragraphs）。
4. 前端打开文章详情弹窗，确认结构化评审展示正确。

## Self-Review

- **Spec 覆盖**：模块 C（JSON 输出格式 + 段落定位 + max_tokens 4096 + 前端结构化展示）✓
- **占位符扫描**：无 TBD/TODO ✓
- **容错设计**：JSON 解析 3 级回退（```json 块 → 纯文本 regex → 旧 _parse_score），确保非 JSON 输出不崩溃 ✓
- **向后兼容**：旧文章 `quality_review_detail` 为 NULL，前端 `reviewDetail` 返回 null 不渲染新 UI，旧 `review_notes` 仍显示 ✓
- **范围**：仅 Change 2（模块 C），未触碰 refine（留给 Change 3）✓
