# Change 1：提示词重构 + 拆 humanize 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把去 AI 味要求并入 generate 提示词并删除 humanize 场景；同时重构 direction/outline/title/generate 四场景提示词，增强结构约束、范例与风格利用。

**Architecture:** 场景提示词存在 DB `scenario_configs.system_prompt_template`，通过新迁移 `022` 用 `UPDATE`/`DELETE` 改写（遵循 019 先例）。`tasks.py` 删除 `trigger_humanize` 任务与 `trigger_generate` 内的同步 humanize 调用，评审触发改为基于 generate 原文。

**Tech Stack:** SQL 迁移（MySQL 语法，dev 跑 SQLite）、Python/Celery（`app/tasks.py`）、pytest。

## Global Constraints

- 注释/提交信息语言：中文；提交格式语义化（`feat:` / `refactor:`）。
- 场景模板变量占位符用双花括号 `{{var}}`，变量名须与 `tasks.py` 注入一致：direction=`{{idea}}`；outline=`{{idea}}` `{{direction}}`；title=`{{idea}}` `{{direction}}` `{{outline}}`；generate=`{{topic}}` `{{direction}}` `{{outline_section}}` `{{word_count_instruction}}`。`{{style_profile}}` 由 Gateway 按 `account_id` 自动注入。
- 禁止 `rm`/`DROP`/`DELETE` 删数据库文件或非本次范围的记录；本计划仅 `DELETE FROM scenario_configs WHERE scenario='humanize'`（用户已授权）。
- dev 库为 SQLite，路径相对 `ArticleGeneratorService/` 解析，迁移/查询必须从该目录执行。

## File Structure

| 文件 | 责任 | 动作 |
|------|------|------|
| `ArticleGeneratorDatabase/migrations/022_update_generation_prompts.sql` | 删 humanize 场景 + 重写四场景模板 | 新建 |
| `ArticleGeneratorService/app/tasks.py` | 删 `trigger_humanize`；`trigger_generate` 移除同步 humanize | 修改 |
| `ArticleGeneratorService/tests/test_change1_humanize_removal.py` | 验证 humanize 已从代码移除 | 新建 |

> 说明：spec 原计划 022 一次性更新六场景模板，但 quality_review（Change 2）和 refine（Change 3）的模板更新会破坏中间状态（JSON 解析/字段尚未就位）。故 022 仅动 direction/outline/title/generate + 删 humanize；quality_review/refine 模板各归各自 change 的迁移。此为 plan 阶段对 spec 迁移拆分的细化。

---

### Task 1: 迁移脚本 022 — 删除 humanize 场景 + 重写四场景提示词

**Files:**
- Create: `ArticleGeneratorDatabase/migrations/022_update_generation_prompts.sql`

**Interfaces:**
- Produces: DB 中 `humanize` 场景记录消失；`direction/outline/title/generate` 四场景的 `system_prompt_template` 被新模板覆盖。

- [ ] **Step 1: 写迁移脚本**

创建 `ArticleGeneratorDatabase/migrations/022_update_generation_prompts.sql`：

```sql
-- 022_update_generation_prompts.sql
-- Change 1：去AI味并入 generate + 四场景提示词增强

-- 模块 A：删除 humanize 场景（去AI味要求已并入 generate 模板）
DELETE FROM scenario_configs WHERE scenario = 'humanize';

-- 模块 B：direction 提示词增强（多样性约束 + 角度类型 + 风格利用）
UPDATE scenario_configs
SET system_prompt_template = '你是一位资深内容策划。根据「想法」和账号写作风格，生成 5 个**互不相同**的写作方向。\n\n## 要求\n1. 每个方向必须是**不同的切入角度**，不得换汤不换药。从以下角度类型中选择互不重叠的组合：\n   - 情感共鸣：从读者情绪、痛点切入\n   - 利益驱动：从读者切身利益、得失切入\n   - 反常识：挑战主流认知，提出对立观点\n   - 实用干货：提供可操作的方法、清单、步骤\n   - 故事叙事：用案例、人物、情节带入\n2. 结合下方账号风格画像的思维模式，而非照搬风格词。\n3. 每个方向一句话，不超过 30 字，要能看出切入角度。\n\n## 账号风格画像\n{{style_profile}}\n\n## 想法\n{{idea}}\n\n## 输出格式（严格 JSON，不要任何额外文字）\n[{"id": "A", "title": "切入角度描述", "angle": "情感共鸣"}, {"id": "B", "title": "切入角度描述", "angle": "反常识"}]',
    description = '② 方向生成：想法 → 5 个不同切入角度（角度类型约束 + 风格利用）'
WHERE scenario = 'direction';

-- 模块 B：outline 提示词增强（结构框架 + 字数占比 + 紧扣方向）
UPDATE scenario_configs
SET system_prompt_template = '你是一位资深内容架构师。根据「想法」「写作方向」和账号风格，生成一份 5-8 个要点的文章大纲。\n\n## 结构要求\n- 大纲要形成完整论证链，建议覆盖：问题/现象引入 → 分析原因 → 给出方案或观点 → 升华收尾（叙事类可用起承转合）。\n- 每个要点用一句话概括核心内容，并在括号内标注预估字数占比（如「约20%」），所有占比合计约 100%。\n- 要点必须紧扣上方的「写作方向」，不得跑题。\n\n## 账号风格画像\n{{style_profile}}\n\n## 输入\n想法：{{idea}}\n写作方向：{{direction}}\n\n## 输出格式（严格 JSON 数组，不要额外文字）\n["要点1（约20%）：核心内容概括", "要点2（约15%）：核心内容概括"]',
    description = '③ 大纲生成：想法+方向 → 5-8 要点大纲（结构框架 + 字数占比）'
WHERE scenario = 'outline';

-- 模块 B：title 提示词增强（few-shot + 风格语感 + 输出纯数组）
UPDATE scenario_configs
SET system_prompt_template = '你是一位爆款标题手。根据「想法」「写作方向」「大纲」和账号风格，生成 5 个候选标题。\n\n## 要求\n1. 简洁有力，15 字以内为佳，最长不超过 20 字。\n2. 准确传达文章核心观点，不标题党、不夸大。\n3. 符合下方账号风格画像里的标题语感；若画像含标题范例，模仿其句式。\n\n## 范例对比\n❌ 差：「随着时代的发展，我们应当重视健康」（套话、空洞）\n✅ 好：「每天走一万步，可能反而伤膝盖」（具体、有信息增量）\n\n## 账号风格画像\n{{style_profile}}\n\n## 输入\n想法：{{idea}}\n写作方向：{{direction}}\n大纲：{{outline}}\n\n## 输出格式（严格 JSON 字符串数组，不要额外文字）\n["标题1", "标题2"]',
    description = '④ 标题生成：想法+方向+大纲 → 5 个候选标题（few-shot + 风格语感）'
WHERE scenario = 'title';

-- 模块 A + B：generate 提示词（保留核心约束骨架 + 内嵌禁用词与反AI要求）
UPDATE scenario_configs
SET system_prompt_template = '你是一位专业的内容创作者。\n\n## 核心约束（最高优先级）\n你必须严格围绕「文章主题」和「写作方向」创作，不得偏离到其他话题。风格要求仅影响表达方式与语气，绝不改变文章的主题和内容方向。\n\n## 文章主题\n{{topic}}\n\n## 写作方向\n{{direction}}\n\n## 写作风格要求（必须严格遵守）\n{{style_profile}}\n\n{{outline_section}}{{word_count_instruction}}\n\n## 去 AI 味硬性要求（与核心约束同等优先级）\n- 禁用套话与套路连接词，以下词语一律不得出现：「总的来说」「综上所述」「首先」「其次」「最后」「换言之」「从某种程度上」「随着」「在当前」「不可或缺」「至关重要」。\n- 段落长短错落，禁止每段都是 3-4 句的整齐结构，偶尔用 1-2 句的短段。\n- 避免三段式对称排比（如「不仅……而且……更……」的堆砌）。\n- 语气自然口语化，像真人说话，不要论文腔。\n- 观点要有具体信息增量（数据、案例、细节），不要空泛议论。\n\n## 其他要求\n- 文章需有吸引人的标题（包含在正文开头）。\n- 结构清晰、内容充实。',
    params = '{"max_tokens": 4096, "temperature": 0.8}',
    description = '⑤ 文章生成：主题+方向+风格+大纲，内嵌禁用词与反AI味要求'
WHERE scenario = 'generate';
```

- [ ] **Step 2: 在 dev SQLite 执行迁移**

从 `ArticleGeneratorService/` 目录执行（SQLite 用 `||` 拼接字符串、不支持 `UPDATE ... SET` 多行换行文本但本脚本每条都是单行字符串字面量，可直接整文件导入）：

```bash
cd ArticleGeneratorService
sqlite3 article_generator.db < ../ArticleGeneratorDatabase/migrations/022_update_generation_prompts.sql
```

- [ ] **Step 3: 查询验证 — humanize 已删除**

```bash
sqlite3 article_generator.db "SELECT scenario FROM scenario_configs WHERE scenario='humanize';"
```
Expected: 无输出（0 行）。

- [ ] **Step 4: 查询验证 — 四场景模板含新关键词**

```bash
sqlite3 article_generator.db "SELECT scenario, system_prompt_template FROM scenario_configs WHERE scenario IN ('direction','outline','title','generate') ORDER BY scenario;" | grep -c "账号风格画像"
```
Expected: `4`（四个场景模板都含「账号风格画像」）。

```bash
sqlite3 article_generator.db "SELECT system_prompt_template FROM scenario_configs WHERE scenario='generate';" | grep -c "不可或缺\|至关重要\|总的来说"
```
Expected: `1`（generate 模板含禁用词清单）。

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorDatabase/migrations/022_update_generation_prompts.sql
git commit -m "feat: 022 迁移重构四场景提示词，删除 humanize 场景"
```

---

### Task 2: 删除 trigger_humanize 任务

**Files:**
- Create: `ArticleGeneratorService/tests/test_change1_humanize_removal.py`
- Modify: `ArticleGeneratorService/app/tasks.py`（删除 `trigger_humanize` 函数，约 261-315 行）

**Interfaces:**
- Consumes: 无
- Produces: `app.tasks` 不再导出 `trigger_humanize`。

- [ ] **Step 1: 写失败的测试**

创建 `ArticleGeneratorService/tests/test_change1_humanize_removal.py`：

```python
"""Change 1：humanize 拆除的回归测试。"""


def test_trigger_humanize_task_removed():
    """模块 A：trigger_humanize celery 任务应已从 app.tasks 删除。"""
    from app import tasks

    assert not hasattr(tasks, "trigger_humanize"), (
        "trigger_humanize 应已删除——humanize 场景已并入 generate，"
        "不再有独立的去AI味任务。"
    )
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd ArticleGeneratorService && pytest tests/test_change1_humanize_removal.py::test_trigger_humanize_task_removed -v
```
Expected: FAIL（`trigger_humanize` 仍存在，`hasattr` 为 True，断言报错）。

- [ ] **Step 3: 删除 trigger_humanize 任务**

在 `ArticleGeneratorService/app/tasks.py` 中，删除整个 `trigger_humanize` 函数（含其上方的 `@celery_app.task(bind=True)` 装饰器，位于 `trigger_generate` 之后、`trigger_refine` 之前，约 261-315 行）。删除后 `trigger_generate` 的结尾直接接 `trigger_refine` 的装饰器。

- [ ] **Step 4: 运行测试验证通过**

```bash
cd ArticleGeneratorService && pytest tests/test_change1_humanize_removal.py::test_trigger_humanize_task_removed -v
```
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py ArticleGeneratorService/tests/test_change1_humanize_removal.py
git commit -m "refactor: 删除 trigger_humanize 任务（去AI味已并入 generate）"
```

---

### Task 3: trigger_generate 移除同步 humanize 调用

**Files:**
- Modify: `ArticleGeneratorService/tests/test_change1_humanize_removal.py`（追加测试）
- Modify: `ArticleGeneratorService/app/tasks.py`（删除 `trigger_generate` 内 humanize 块，约 206-228 行）

**Interfaces:**
- Consumes: Task 2 已删除 `trigger_humanize`。
- Produces: `trigger_generate` 生成后直接落库，评审基于 generate 原文 `article.content`。

- [ ] **Step 1: 追加失败的测试**

在 `ArticleGeneratorService/tests/test_change1_humanize_removal.py` 末尾追加：

```python
import inspect


def test_trigger_generate_does_not_call_humanize():
    """模块 A：trigger_generate 不再发起 humanize /chat 调用。"""
    from app import tasks

    src = inspect.getsource(tasks.trigger_generate)
    assert "humanize" not in src, (
        "trigger_generate 不应再包含任何 humanize 调用——生成完直接落库，"
        "去AI味要求已在 generate 提示词中。"
    )


def test_trigger_generate_still_triggers_reviews():
    """模块 A：删除 humanize 后，质量/合规评审仍被触发（基于 generate 原文）。"""
    from app import tasks

    src = inspect.getsource(tasks.trigger_generate)
    assert "trigger_quality_review" in src, "质量评审触发不应被误删"
    assert "trigger_compliance_review" in src, "合规评审触发不应被误删"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd ArticleGeneratorService && pytest tests/test_change1_humanize_removal.py::test_trigger_generate_does_not_call_humanize -v
```
Expected: FAIL（`trigger_generate` 源码仍含 "humanize" 字样——206-228 行的注释和调用）。

- [ ] **Step 3: 删除 trigger_generate 内的 humanize 块**

在 `ArticleGeneratorService/app/tasks.py` 的 `trigger_generate` 中，删除「生成成功后同步 humanize」整段（约 206-228 行），即从注释行：

```python
        # 生成成功后，同步执行去AI味（确保前端拿到的是最终内容，防止竞态）
        # quality_review 和 compliance_review 不修改 content，可保持异步
        humanized = content
        try:
            llm_url = settings.llm_service_url.rstrip("/")
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(f"{llm_url}/chat", json={
                    "scenario": "humanize",
                    "task_id": self.request.id,
                    "variables": {
                        "article_content": content,
                        "outline_section": outline_section,
                    },
                })
                resp.raise_for_status()
                data = resp.json()
            humanized = data.get("content", "") or content
            if humanized and humanized != content:
                article.content = humanized
                db.commit()
        except Exception:
            # humanize 失败不影响主流程，保留原始内容
            pass
```

**全部删除**。删除后，紧跟在 `db.commit()` / `db.refresh(article)`（热点状态更新块）之后的应是「更新任务状态」注释块：

```python
        # 更新任务状态
        if gt:
            gt.status = "success"
            gt.article_id = article.id
            db.commit()
```

`article.content` 此时保持为 generate 原文（188-194 行写入），后续 `trigger_quality_review.delay(article.id, article.content)` 自动基于原文评审，无需改动评审触发代码。

- [ ] **Step 4: 运行测试验证通过**

```bash
cd ArticleGeneratorService && pytest tests/test_change1_humanize_removal.py -v
```
Expected: 3 个测试全部 PASS。

- [ ] **Step 5: 跑全量回归**

```bash
cd ArticleGeneratorService && pytest tests/ -v
```
Expected: 全部 PASS。重点关注 `test_generate_prompt_consolidation.py`（现有 generate payload 测试不应被破坏——本次只删 humanize，未改 generate 的 variables 构造）。

- [ ] **Step 6: Commit**

```bash
git add ArticleGeneratorService/app/tasks.py ArticleGeneratorService/tests/test_change1_humanize_removal.py
git commit -m "refactor: trigger_generate 移除同步 humanize，评审基于 generate 原文"
```

---

## 手动验证（端到端冒烟）

单元测试只能验证「humanize 已移除」。提示词增强的实际效果需手动跑一次生成链路确认：

1. 重启后端 + Celery（`./scripts/start.sh` 或单独重启 Celery worker——新任务需清 pycache 避免旧 worker，见 memory `celery-worker-lifecycle`）。
2. 前端触发生成一篇文章，完成后查 `generation_logs`：
   ```bash
   sqlite3 ArticleGeneratorService/article_generator.db "SELECT scenario, status FROM generation_logs WHERE task_id='<本次 task_id>' ORDER BY id;"
   ```
   Expected: 只有 `generate` + `quality_review` + `compliance_review`，**无 `humanize`**。
3. 查生成文章是否含禁用词：
   ```bash
   sqlite3 ArticleGeneratorService/article_generator.db "SELECT content FROM articles WHERE id=<本次文章 id>;" | grep -o "总的来说\|综上所述\|不可或缺\|至关重要"
   ```
   Expected: 无输出（generate 提示词已禁用这些词）。
4. 触发一次 direction/outline/title，确认输出仍是合法 JSON（新模板强化了 JSON 格式约束，解析器应正常工作）。

## Self-Review

- **Spec 覆盖**：模块 A（删 humanize 场景 → Task 1 Step DELETE；删 trigger_humanize → Task 2；删同步调用 → Task 3）✓；模块 B（direction/outline/title/generate 模板增强 → Task 1 UPDATE）✓。generate 内嵌禁用词与反AI要求 → Task 1 generate UPDATE ✓。
- **占位符扫描**：无 TBD/TODO，所有 SQL 与测试代码完整 ✓。
- **类型一致**：变量名（`{{idea}}` `{{direction}}` `{{outline}}` `{{topic}}` `{{outline_section}}` `{{word_count_instruction}}` `{{style_profile}}`）与 `tasks.py` 现有注入一致 ✓。
- **范围**：仅 Change 1（模块 A+B），未触碰 quality_review/refine 模板与代码（留给 Change 2/3）✓。
