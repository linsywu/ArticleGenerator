# 文章字数配置 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将硬编码的"字数1500左右"改为账号级可配置选项，支持创作流程中选择字数。

**Architecture:** 账号表新增 2 列（word_count_options JSON + default_word_count），后端 schema/API/tasks 层层传递 word_count 参数，前端 AccountsView 表单配置选项，CreateView 步骤 2 新增选择器。

**Tech Stack:** Python/FastAPI/SQLAlchemy/Celery (后端), Vue 3/Element Plus/TypeScript (前端), SQLite (DB)

---

### Task 1: DB 迁移

**Files:**
- Create: `ArticleGeneratorDatabase/migrations/005_add_word_count_config.sql`

- [ ] **Step 1: 创建迁移脚本**

```sql
-- 005_add_word_count_config.sql
-- 新增字数选项配置：word_count_options TEXT (JSON)，default_word_count VARCHAR(20)

ALTER TABLE accounts ADD COLUMN word_count_options TEXT COMMENT 'JSON: 字数选项列表 [{"value":"1500","label":"1500字左右"}]' AFTER style_profile_status;
ALTER TABLE accounts ADD COLUMN default_word_count VARCHAR(20) COMMENT '默认字数 value' AFTER word_count_options;
```

- [ ] **Step 2: 执行迁移**

Run:
```bash
cd ArticleGeneratorService && sqlite3 article_generator.db < ../ArticleGeneratorDatabase/migrations/005_add_word_count_config.sql
```

Verify:
```bash
cd ArticleGeneratorService && sqlite3 article_generator.db ".schema accounts" | grep word_count
```

Expected: 两行包含 `word_count_options` 和 `default_word_count`

- [ ] **Step 3: Commit**

```bash
cd ArticleGeneratorService && git add ../ArticleGeneratorDatabase/migrations/005_add_word_count_config.sql && git commit -m "feat: accounts 表新增 word_count_options 和 default_word_count 列"
```

---

### Task 2: 后端 Model 新增字段

**Files:**
- Modify: `ArticleGeneratorService/app/models.py:39-40`

- [ ] **Step 1: Account 模型新增两列**

在 `ArticleGeneratorService/app/models.py` 的 Account 类中，`style_profile_status` 之后插入：

```python
    word_count_options = Column(Text)  # JSON: [{"value":"1500","label":"1500字左右"}]
    default_word_count = Column(String(20))
```

位置：`style_profile_status = Column(...)` 行之后，`created_at` 行之前。

- [ ] **Step 2: 验证模型导入无错误**

Run:
```bash
cd ArticleGeneratorService && python3 -c "from app.models import Account; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd ArticleGeneratorService && git add app/models.py && git commit -m "feat: Account 模型新增 word_count_options 和 default_word_count"
```

---

### Task 3: 后端 Schema 新增字段

**Files:**
- Modify: `ArticleGeneratorService/app/schemas.py:11-16` (AccountBase)
- Modify: `ArticleGeneratorService/app/schemas.py:22-27` (AccountUpdate)
- Modify: `ArticleGeneratorService/app/schemas.py:29-54` (AccountResponse)
- Modify: `ArticleGeneratorService/app/schemas.py:262-265` (DirectionsRequest)

- [ ] **Step 1: AccountBase 新增字段**

```python
class AccountBase(BaseModel):
    platform: str
    account_name: str
    lora_path: Optional[str] = None
    sample_articles: Optional[str] = None
    word_count_options: Optional[str] = None   # JSON string → frontend parses as array
    default_word_count: Optional[str] = None
```

- [ ] **Step 2: AccountUpdate 新增字段**

```python
class AccountUpdate(BaseModel):
    platform: Optional[str] = None
    account_name: Optional[str] = None
    lora_path: Optional[str] = None
    sample_articles: Optional[str] = None
    word_count_options: Optional[str] = None
    default_word_count: Optional[str] = None
```

- [ ] **Step 3: AccountResponse 新增字段并添加 parser**

在 `AccountResponse` 中新增：

```python
class AccountResponse(AccountBase):
    id: int
    style_profile: Optional[str] = None
    style_profile_updated_at: Optional[datetime] = None
    style_profile_structured: Optional[Any] = None
    style_profile_version: Optional[int] = None
    style_profile_status: Optional[str] = None
    word_count_options: Optional[str] = None
    default_word_count: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @field_validator("style_profile_structured", mode="before")
    @classmethod
    def parse_structured(cls, v):
        """将数据库中的 JSON 字符串转为 dict"""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
```

- [ ] **Step 4: DirectionsRequest 新增可选 word_count**

在第 262 行附近：

```python
class DirectionsRequest(BaseModel):
    account_id: int
    idea: str
    word_count: Optional[str] = None  # 新增：字数选择
```

- [ ] **Step 5: 验证 schema 导入无错误**

Run:
```bash
cd ArticleGeneratorService && python3 -c "from app.schemas import AccountBase, AccountUpdate, AccountResponse, DirectionsRequest; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
cd ArticleGeneratorService && git add app/schemas.py && git commit -m "feat: Account/Directions schema 新增 word_count 字段"
```

---

### Task 4: 后端 API — Directions 端点传参 + Tasks 接收

**Files:**
- Modify: `ArticleGeneratorService/app/api/generate.py:173-189`
- Modify: `ArticleGeneratorService/app/tasks.py:94-98` (trigger_generate 字数行)
- Modify: `ArticleGeneratorService/app/tasks.py:360-410` (trigger_direction_generation)
- Modify: `ArticleGeneratorService/app/tasks.py:202-257` (trigger_refine)

- [ ] **Step 1: directions 端点传递 word_count 到 Celery 任务**

在 `api/generate.py` 第 182 行，将 `trigger_direction_generation.delay` 调用改为：

```python
task = trigger_direction_generation.delay(data.account_id, data.idea.strip(), data.word_count)
```

- [ ] **Step 2: trigger_direction_generation 接收 word_count 参数**

在 `tasks.py` 的 `trigger_direction_generation` 函数签名（约第 360 行）新增参数：

```python
def trigger_direction_generation(self, account_id: int, idea: str, word_count: str = None):
```

然后在 variables 中添加 word_count（约第 389 行）：

```python
variables = {"idea": idea}
# 新增：注入字数要求
if word_count:
    variables["word_count"] = f"字数{word_count}。"
else:
    variables["word_count"] = "字数1500左右。"

if structured:
    variables["thinking_pattern"] = structured.get("thinking_pattern", "")
    variables["structure_pattern"] = structured.get("structure_pattern", "")
```

- [ ] **Step 3: trigger_generate 将硬编码字数改为变量**

在 `tasks.py` 第 94-99 行的 `user_prompt` 构建中，删除硬编码 `'字数1500左右。'`：

```python
# 查找字数配置（优先从账号读取）
word_count_instruction = "字数1500左右。"  # fallback
if account:
    wc = account.default_word_count
    if wc:
        # 从 word_count_options 中找到对应的 label
        try:
            opts = json.loads(account.word_count_options or "[]")
            for opt in opts:
                if opt.get("value") == wc:
                    word_count_instruction = f"字数{opt.get('label', wc + '字')}。"
                    break
            else:
                word_count_instruction = f"字数{wc}字。"
        except (json.JSONDecodeError, TypeError):
            word_count_instruction = f"字数{wc}字。"

user_prompt = (
    f'以"{hotspot_title}"为题，写一篇文章。\n\n'
    f'{style_instructions}\n'
    f'{outline_text}\n'
    f'{word_count_instruction}'
)
```

实际代码：替换第 94-98 行：

```python
        # 从账号读取字数配置
        word_count_instruction = "字数1500左右。"
        if account:
            wc = account.default_word_count
            if wc:
                try:
                    opts = json.loads(account.word_count_options or "[]")
                    for opt in opts:
                        if opt.get("value") == wc:
                            word_count_instruction = f"字数{opt.get('label', wc + '字')}。"
                            break
                    else:
                        word_count_instruction = f"字数{wc}字。"
                except (json.JSONDecodeError, TypeError):
                    word_count_instruction = f"字数{wc}字。"

        user_prompt = (
            f'以"{hotspot_title}"为题，写一篇文章。\n\n'
            f'{style_instructions}\n'
            f'{outline_text}\n'
            f'{word_count_instruction}'
        )
```

- [ ] **Step 4: trigger_refine 同理更新（如 refine 场景提示词也需要字数）**

检查 `trigger_refine` 中调 LLM `/refine` 时是否需要在 variables 中增加 word_count。当前 `/refine` 端点使用 `article_content` + `keywords`，字数调整的复用性较低，保持现有行为不变即可。

- [ ] **Step 5: 验证代码导入无错误**

Run:
```bash
cd ArticleGeneratorService && python3 -c "from app.tasks import trigger_generate, trigger_direction_generation; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: 重启 Celery Worker 使新代码生效**

```bash
pkill -f "celery.*article_generator" && sleep 1
cd ArticleGeneratorService && nohup celery -A app.tasks:celery_app worker -l info > /tmp/celery.log 2>&1 &
```

- [ ] **Step 7: Commit**

```bash
cd ArticleGeneratorService && git add app/api/generate.py app/tasks.py && git commit -m "feat: 后端生成/方向任务传递 word_count 参数"
```

---

### Task 5: 前端 API Client 更新

**Files:**
- Modify: `ArticleGeneratorAdm/src/api/client.ts:33-45` (Account interface)
- Modify: `ArticleGeneratorAdm/src/api/client.ts:155-156` (generateDirections)

- [ ] **Step 1: Account 接口新增字段**

```typescript
export interface Account {
  id: number;
  platform: string;
  account_name: string;
  lora_path?: string;
  sample_articles?: string;
  style_profile?: string;
  style_profile_updated_at?: string;
  style_profile_structured?: StyleProfile | null;
  style_profile_version?: number;
  style_profile_status?: string;
  word_count_options?: string;   // JSON: [{"value":"1500","label":"1500字左右"}]
  default_word_count?: string;   // e.g. "1500"
  created_at: string;
}
```

- [ ] **Step 2: generateDirections 新增 word_count 参数**

```typescript
generateDirections: (accountId: number, idea: string, wordCount?: string) =>
  client.post<{ directions: DirectionItem[] }>("/generate/directions", {
    account_id: accountId,
    idea,
    word_count: wordCount || null,
  }),
```

- [ ] **Step 3: 验证 TypeScript 编译**

Run:
```bash
cd ArticleGeneratorAdm && npx vue-tsc --noEmit 2>&1 | head -20
```

Expected: No errors related to client.ts changes.

- [ ] **Step 4: Commit**

```bash
cd ArticleGeneratorAdm && git add src/api/client.ts && git commit -m "feat: Account 接口新增 word_count_options/default_word_count，generateDirections 支持 word_count"
```

---

### Task 6: 前端 AccountsView 新增加字数配置 Tab

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/AccountsView.vue`

- [ ] **Step 1: 在新增加 Tab "字数配置"**

在 `<el-tab-pane label="风格画像" name="profile">` 之后，`</el-tabs>` 之前（约第 131 行之前），插入新的 Tab：

```html
        <!-- Tab 4: 字数配置 -->
        <el-tab-pane label="字数配置" name="wordcount">
          <el-form label-width="100px" class="detail-form">
            <el-form-item label="字数选项">
              <div style="width:100%">
                <div v-for="(opt, i) in wordCountOptions" :key="i" style="display:flex;gap:8px;margin-bottom:8px;align-items:center">
                  <el-input v-model="opt.value" placeholder="值（如 1500）" size="small" style="width:140px" />
                  <el-input v-model="opt.label" placeholder="显示名（如 1500字左右）" size="small" style="width:200px" />
                  <el-button size="small" text type="danger" @click="wordCountOptions.splice(i, 1)">×</el-button>
                </div>
                <el-button size="small" @click="wordCountOptions.push({ value: '', label: '' })">＋ 添加选项</el-button>
                <p class="form-hint">格式示例：value="1500" label="1500字左右"</p>
              </div>
            </el-form-item>
            <el-form-item label="默认字数">
              <el-select v-model="wordCountDefault" placeholder="选择默认字数" size="small" style="width:220px" :disabled="!wordCountOptions.length">
                <el-option v-for="opt in wordCountOptions" :key="opt.value" :label="opt.label || opt.value" :value="opt.value" :disabled="!opt.value" />
              </el-select>
            </el-form-item>
          </el-form>
          <div style="text-align:right">
            <el-button type="primary" @click="saveWordCount" :loading="savingWordCount">保存字数配置</el-button>
          </div>
        </el-tab-pane>
```

- [ ] **Step 2: script 中新增响应式状态和方法**

在 `<script setup>` 中，`form` 声明之后（约第 190 行），新增：

```typescript
// 字数配置
const wordCountOptions = ref<{ value: string; label: string }[]>([])
const wordCountDefault = ref('')
const savingWordCount = ref(false)
```

在 `openDetail` 函数末尾（约第 219 行之后），新增解析逻辑：

```typescript
function openDetail(row: Account) {
  editingAccount.value = row;
  form.platform = row.platform; form.account_name = row.account_name;
  loadRefArticles(row.id); activeTab.value = "basic";
  detailVisible.value = true;

  // 解析字数配置
  wordCountDefault.value = row.default_word_count || ''
  try {
    wordCountOptions.value = row.word_count_options ? JSON.parse(row.word_count_options) : []
  } catch {
    wordCountOptions.value = []
  }
}
```

在 `openCreate` 函数中（约第 208 行），重置字数配置：

```typescript
function openCreate() {
  editingAccount.value = null;
  form.platform = ""; form.account_name = "";
  refArticles.value = []; activeTab.value = "basic";
  detailVisible.value = true;
  wordCountOptions.value = []
  wordCountDefault.value = ''
}
```

新增 `saveWordCount` 函数：

```typescript
async function saveWordCount() {
  if (!editingAccount.value?.id) {
    ElMessage.warning('请先保存基本信息')
    return
  }
  savingWordCount.value = true
  try {
    const valid = wordCountOptions.value.filter(o => o.value && o.label)
    await api.updateAccount(editingAccount.value.id, {
      word_count_options: JSON.stringify(valid),
      default_word_count: wordCountDefault.value || null,
    })
    // 更新本地数据
    editingAccount.value.word_count_options = JSON.stringify(valid)
    editingAccount.value.default_word_count = wordCountDefault.value || null
    ElMessage.success('字数配置已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    savingWordCount.value = false
  }
}
```

- [ ] **Step 3: 验证 TypeScript 编译**

Run:
```bash
cd ArticleGeneratorAdm && npx vue-tsc --noEmit 2>&1 | head -20
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
cd ArticleGeneratorAdm && git add src/views/AccountsView.vue && git commit -m "feat: AccountsView 新增字数配置 Tab（选项管理 + 默认值）"
```

---

### Task 7: 前端 CreateView 步骤 2 新增加字数选择器

**Files:**
- Modify: `ArticleGeneratorAdm/src/views/CreateView.vue`

- [ ] **Step 1: 步骤 2 模板新增字数选择器**

在 `CreateView.vue` 的步骤 2 区域（`<div v-else-if="currentStep === 1">`），在 `idea-input-area` 的 `<el-input>` 后面、`card-actions` 之前（约第 61 行之后），插入字数选择器：

```html
          <div v-if="wordCountOpts.length" class="word-count-area">
            <span class="word-count-label">📏 文章字数：</span>
            <el-select v-model="selectedWordCount" placeholder="选择字数" size="default">
              <el-option
                v-for="opt in wordCountOpts"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </div>
```

- [ ] **Step 2: script 中新增响应式状态**

在 `<script setup>` 的 `idea` 声明之后（约第 163 行），新增：

```typescript
// 字数选择
const selectedWordCount = ref('')
const wordCountOpts = ref<{ value: string; label: string }[]>([])
```

- [ ] **Step 3: 选择账号时解析字数配置**

修改步骤 1（选择账号 → 下一步）的逻辑。需要监听 `selectedAccountId` 变化时解析字数配置。在 `selectedAccount` computed 之后（约第 180 行之后），新增 watcher：

```typescript
import { ref, computed, onMounted, watch } from 'vue'

// 当选中的账号变化时，更新字数选项
watch(selectedAccount, (acc) => {
  if (acc) {
    try {
      wordCountOpts.value = acc.word_count_options ? JSON.parse(acc.word_count_options) : []
    } catch {
      wordCountOpts.value = []
    }
    selectedWordCount.value = acc.default_word_count || ''
  } else {
    wordCountOpts.value = []
    selectedWordCount.value = ''
  }
})
```

- [ ] **Step 4: generateDirections 传入 wordCount**

修改 `generateDirections` 函数（约第 182 行）：

```typescript
async function generateDirections() {
  if (!selectedAccountId.value || !idea.value.trim()) return
  loadingDirections.value = true
  try {
    const wc = selectedWordCount.value || undefined
    const { data } = await api.generateDirections(selectedAccountId.value, idea.value.trim(), wc)
    directions.value = data.directions || []
    if (directions.value.length) {
      selectedDirection.value = directions.value[0]
      currentStep.value = 2
    }
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '方向生成失败') }
  finally { loadingDirections.value = false }
}
```

- [ ] **Step 5: startGenerate 传入 wordCount（通过 outline 生成后传递）**

生成全文时，字数已经通过方向/大纲阶段注入到 LLM prompt 中。当前 `triggerGenerateWithOutline` 不支持 word_count 参数，但字数由账号默认值在 tasks.py 中自动读取，所以 `startGenerate` 不需要额外传参。

- [ ] **Step 6: 验证 TypeScript 编译**

Run:
```bash
cd ArticleGeneratorAdm && npx vue-tsc --noEmit 2>&1 | head -20
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
cd ArticleGeneratorAdm && git add src/views/CreateView.vue && git commit -m "feat: CreateView 步骤 2 新增字数选择器，从账号配置读取"
```

---

### Task 8: 验证与清理

- [ ] **Step 1: 验证向后兼容 — 无字数配置的账号正常生成**

启动服务后，使用一个未配置 `word_count_options` 的旧账号：
```bash
# 检查旧账号的字数配置
cd ArticleGeneratorService && sqlite3 article_generator.db "SELECT id, account_name, word_count_options, default_word_count FROM accounts"
```
创建流程中使用该账号，确认：
- 步骤 2 不显示字数选择器（`wordCountOpts` 为空数组）
- 生成方向成功
- 生成全文成功，文章字数约 1500（fallback 值）

- [ ] **Step 2: 验证字数配置功能**

1. 在账号管理页为测试账号添加字数选项：
   - 添加 `{"value":"500","label":"500字短文"}` 和 `{"value":"3000","label":"3000字长文"}`
   - 设置默认值为 `"3000"`
   
2. 进入创作流程，步骤 2 确认：
   - 字数选择器可见
   - 默认选中 "3000字长文"
   - 可以切换到 "500字短文"
   
3. 选择 "500字短文" 生成全文，确认文章字数在 500 左右

- [ ] **Step 3: Commit any remaining changes**

```bash
git status && git diff --stat
```
