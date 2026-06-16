<template>
  <div class="create-view">
    <!-- 页面标题 -->
    <header class="page-header">
      <h1 class="page-title">文章创作</h1>
      <p class="page-subtitle">选择账号风格，输入想法，系统辅助生成高质量文章</p>
    </header>

    <!-- 步骤条 -->
    <div class="steps-wrapper">
      <div class="custom-steps">
        <div
          v-for="(step, i) in steps"
          :key="i"
          class="step-dot"
          :class="{ active: i === currentStep, done: i < currentStep, pending: i > currentStep }"
        >
          <span class="step-number">{{ i < currentStep ? '✓' : i + 1 }}</span>
          <span class="step-label">{{ step }}</span>
          <span v-if="i < 5" class="step-line" :class="{ filled: i < currentStep }"></span>
        </div>
      </div>
    </div>

    <!-- 步骤内容 -->
    <div class="step-content">
      <transition name="step-trans" mode="out-in">
        <!-- 步骤 1: 选择账号 -->
        <div v-if="currentStep === 0" key="step1" class="step-card">
          <div class="card-header">
            <span class="card-number">01</span>
            <h2 class="card-title">选择写作账号</h2>
          </div>
          <p class="card-desc">选定一个风格账号，后续方向、大纲、全文都将基于该风格创作。</p>
          <div class="account-select-area">
            <div v-for="acc in accounts" :key="acc.id" class="account-option" :class="{ selected: selectedAccountId === acc.id }" @click="selectedAccountId = acc.id">
              <div class="account-avatar">{{ acc.account_name.charAt(0) }}</div>
              <div class="account-info">
                <span class="account-name">{{ acc.account_name }}</span>
                <span class="account-platform">{{ acc.platform }}</span>
              </div>
              <span class="account-badge" :class="{ ready: acc.style_profile_status === 'ready' }">
                {{ acc.style_profile_status === 'ready' ? '画像就绪' : '待蒸馏' }}
              </span>
              <span v-if="selectedAccountId === acc.id" class="account-check">✓</span>
            </div>
          </div>
          <div class="card-actions">
            <el-button size="large" type="primary" :disabled="!selectedAccountId" @click="currentStep = 1">下一步 · 输入想法</el-button>
          </div>
        </div>

        <!-- 步骤 2: 输入想法 -->
        <div v-else-if="currentStep === 1" key="step2" class="step-card">
          <div class="card-header">
            <span class="card-number">02</span>
            <h2 class="card-title">输入创作想法</h2>
          </div>
          <p class="card-desc">基于 <strong>{{ selectedAccount?.account_name }}</strong> 的风格进行创作。</p>
          <div class="idea-input-area">
            <el-input v-model="idea" type="textarea" :rows="6" placeholder="例如：AI 编程工具让初级程序员感到焦虑，但这个焦虑可能被夸大了..." class="idea-textarea" />
            <div class="idea-hints">
              <span class="hint-label">💡 试试这些：</span>
              <span class="hint-tag" @click="idea = '最近 AI 编程工具越来越强，初级程序员还有必要学基础吗？'">AI 与程序员焦虑</span>
              <span class="hint-tag" @click="idea = '在信息爆炸的时代，深度阅读变成了一种稀缺能力'">深度阅读的价值</span>
              <span class="hint-tag" @click="idea = '大厂裁员潮下，技术人员该如何构建自己的护城河？'">技术人的护城河</span>
            </div>
          </div>
          <div v-if="wordCountOpts.length" class="word-count-area">
            <span class="word-count-label">📏 文章字数：</span>
            <el-select v-model="selectedWordCount" placeholder="选择字数" size="default" style="width:240px">
              <el-option v-for="opt in wordCountOpts" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </div>
          <div class="card-actions">
            <el-button size="large" @click="currentStep = 0">返回上一步</el-button>
            <el-button size="large" type="primary" :disabled="!idea.trim()" :loading="loadingDirections" @click="generateDirections">
              生成写作方向
            </el-button>
          </div>
        </div>

        <!-- 步骤 3: 选择写作方向 -->
        <div v-else-if="currentStep === 2" key="step3" class="step-card">
          <div class="card-header">
            <span class="card-number">03</span>
            <h2 class="card-title">选择写作方向</h2>
          </div>
          <p class="card-desc">基于"{{ idea }}"生成了以下写作方向，选择一个继续。</p>
          <div v-if="directions.length" class="directions-grid">
            <div v-for="d in directions" :key="d.id" class="direction-card" :class="{ selected: selectedDirection?.id === d.id }" @click="selectedDirection = d">
              <span class="direction-id">{{ d.id }}</span>
              <span class="direction-title">{{ d.title }}</span>
              <span v-if="selectedDirection?.id === d.id" class="direction-check">✓</span>
            </div>
          </div>
          <div v-else class="loading-state">
            <el-icon class="is-loading"><span>⏳</span></el-icon>
            <span>正在生成方向...</span>
          </div>
          <div class="card-actions">
            <el-button size="large" @click="currentStep = 1">返回上一步</el-button>
            <el-button size="large" type="primary" :disabled="!selectedDirection" :loading="loadingOutline" @click="generateOutline">
              下一步 · 生成大纲
            </el-button>
          </div>
        </div>

        <!-- 步骤 4: 确认大纲 -->
        <div v-else-if="currentStep === 3" key="step4" class="step-card">
          <div class="card-header">
            <span class="card-number">04</span>
            <h2 class="card-title">确认大纲</h2>
          </div>
          <p class="card-desc">方向：{{ selectedDirection?.title }}。编辑、排序或增删要点。</p>
          <div v-if="outline.length" class="outline-list">
            <div v-for="(item, i) in outline" :key="i" class="outline-row">
              <span class="outline-order">{{ i + 1 }}</span>
              <el-input v-model="outline[i].point" size="small" class="outline-input" />
              <el-button size="small" text @click="moveOutlineUp(i)" :disabled="i === 0">↑</el-button>
              <el-button size="small" text @click="moveOutlineDown(i)" :disabled="i === outline.length - 1">↓</el-button>
              <el-button size="small" text type="danger" @click="outline.splice(i, 1)">×</el-button>
            </div>
          </div>
          <el-button size="small" @click="outline.push({ order: outline.length + 1, point: '' })" style="margin-top:12px">＋ 添加要点</el-button>
          <div class="card-actions">
            <el-button size="large" @click="currentStep = 2">返回上一步</el-button>
            <el-button size="large" type="primary" :disabled="!outline.length || !outline.every(o => o.point.trim())" :loading="loadingTitles" @click="generateTitles">
              生成候选标题
            </el-button>
          </div>
        </div>

        <!-- 步骤 5: 选择标题 -->
        <div v-else-if="currentStep === 4" key="step5" class="step-card">
          <div class="card-header">
            <span class="card-number">05</span>
            <h2 class="card-title">选择文章标题</h2>
          </div>
          <p class="card-desc">方向：{{ selectedDirection?.title }}。选择一个标题，或编辑后使用。</p>
          <div v-if="titles.length" class="titles-grid">
            <div v-for="(t, i) in titles" :key="i" class="title-card" :class="{ selected: selectedTitle === t }" @click="selectedTitle = t">
              <span class="title-id">{{ i + 1 }}</span>
              <span class="title-text">{{ t }}</span>
              <span v-if="selectedTitle === t" class="title-check">✓</span>
            </div>
          </div>
          <div v-else class="loading-state">
            <span>⏳ 正在生成标题...</span>
          </div>
          <div v-if="titles.length" class="title-edit-area">
            <el-input v-model="selectedTitle" placeholder="编辑选中的标题..." size="default" />
          </div>
          <div class="card-actions">
            <el-button size="large" @click="currentStep = 3">返回修改大纲</el-button>
            <el-button size="large" type="primary" :disabled="!selectedTitle.trim()" @click="startGenerate">
              生成全文
            </el-button>
          </div>
        </div>

        <!-- 步骤 6: 生成全文 -->
        <div v-else key="step6" class="step-card">
          <div class="card-header">
            <span class="card-number">06</span>
            <h2 class="card-title">生成全文</h2>
          </div>
          <div v-if="generating" class="generating-state">
            <div class="generating-spinner"></div>
            <p class="generating-text">{{ generatingStatusText }}</p>
          </div>
          <div v-else-if="generatedArticle" class="article-result">
            <div class="article-content">{{ generatedArticle }}</div>
            <div class="card-actions">
              <el-button size="large" @click="currentStep = 4">返回修改标题</el-button>
              <el-button size="large" type="primary" @click="submitForReview">提交评审</el-button>
            </div>
          </div>
          <div v-else class="card-actions">
            <el-button size="large" @click="currentStep = 4">返回上一步</el-button>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type Account, type DirectionItem, type OutlinePoint } from '@/api/client'

const steps = ['选择账号', '输入想法', '写作方向', '确认大纲', '选择标题', '生成全文']
const currentStep = ref(0)
const accounts = ref<Account[]>([])
const selectedAccountId = ref<number | null>(null)
const idea = ref('')

// 字数选择（从账号选项读取）
const selectedWordCount = ref('')
const wordCountOpts = ref<string[]>([])

// 步骤 3
const directions = ref<DirectionItem[]>([])
const selectedDirection = ref<DirectionItem | null>(null)
const loadingDirections = ref(false)

// 步骤 4
const outline = ref<OutlinePoint[]>([])
const loadingOutline = ref(false)

// 步骤 5 — 标题
const titles = ref<string[]>([])
const selectedTitle = ref('')
const loadingTitles = ref(false)

// 步骤 6
const generating = ref(false)
const generatingStatusText = ref('')
const generatedArticle = ref('')
const generatedArticleId = ref<number | null>(null)

const selectedAccount = computed(() => accounts.value.find(a => a.id === selectedAccountId.value) || null)

// 当选中账号变化时，加载字数选项
watch(selectedAccount, (acc) => {
  if (acc) {
    try {
      wordCountOpts.value = acc.word_count_options ? JSON.parse(acc.word_count_options) : []
    } catch {
      wordCountOpts.value = []
    }
    selectedWordCount.value = acc.word_count || ''
  } else {
    wordCountOpts.value = []
    selectedWordCount.value = ''
  }
})

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

async function generateOutline() {
  if (!selectedAccountId.value || !selectedDirection.value) return
  loadingOutline.value = true
  try {
    const { data } = await api.generateOutline(selectedAccountId.value, idea.value.trim(), selectedDirection.value.title)
    outline.value = data.outline || []
    if (outline.value.length) currentStep.value = 3
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '大纲生成失败') }
  finally { loadingOutline.value = false }
}

function moveOutlineUp(i: number) { if (i > 0) { const t = outline.value[i]; outline.value[i] = outline.value[i-1]; outline.value[i-1] = t } }
function moveOutlineDown(i: number) { if (i < outline.value.length - 1) { const t = outline.value[i]; outline.value[i] = outline.value[i+1]; outline.value[i+1] = t } }

async function generateTitles() {
  if (!selectedAccountId.value || !selectedDirection.value) return
  loadingTitles.value = true
  try {
    const points = outline.value.map(o => o.point)
    const { data } = await api.generateTitles(selectedAccountId.value, idea.value.trim(), selectedDirection.value.title, points)
    titles.value = data.titles || []
    if (titles.value.length) {
      selectedTitle.value = titles.value[0]
      currentStep.value = 4
    }
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '标题生成失败') }
  finally { loadingTitles.value = false }
}

async function startGenerate() {
  if (!selectedAccountId.value || !idea.value.trim() || !selectedTitle.value.trim()) return
  generating.value = true
  currentStep.value = 5

  try {
    const points = outline.value.map(o => o.point)
    const wc = selectedWordCount.value || undefined
    const topic = selectedTitle.value.trim()
    const { data } = await api.triggerGenerateWithOutline(selectedAccountId.value, topic, points, wc)
    generating.value = false
    // Reset flow
    currentStep.value = 0
    idea.value = ''
    directions.value = []
    selectedDirection.value = null
    outline.value = []
    titles.value = []
    selectedTitle.value = ''
    ElMessage.success('已加入任务中心')
  } catch (e: any) {
    ElMessage.error(e?.message || '生成失败')
    generating.value = false
  }
}

async function submitForReview() {
  if (!generatedArticleId.value) return
  try {
    await api.updateArticleStatus(generatedArticleId.value, 'approved')
    ElMessage.success('已提交评审队列')
    // 重置流程
    currentStep.value = 0
    idea.value = ''
    directions.value = []
    selectedDirection.value = null
    outline.value = []
    generatedArticle.value = ''
    generatedArticleId.value = null
  } catch (e: any) { ElMessage.error('提交失败') }
}

onMounted(async () => {
  try {
    const resp = await api.getAccounts()
    accounts.value = resp.data as Account[]
    if (accounts.value.length) selectedAccountId.value = accounts.value[0].id
  } catch (e) { console.error('加载账号失败', e) }
})
</script>

<style scoped>
/* existing styles from current CreateView.vue — keep them all */
.create-view { max-width: 860px; margin: 0 auto; }
.page-header { margin-bottom: var(--space-xl); }
.page-title { font-family: var(--font-serif); font-size: 28px; font-weight: 900; color: var(--text-on-dark); letter-spacing: 1px; margin-bottom: 6px; }
.page-subtitle { font-size: 14px; color: var(--text-muted); letter-spacing: 0.3px; }

.steps-wrapper { margin-bottom: var(--space-2xl); }
.custom-steps { display: flex; align-items: center; justify-content: center; }
.step-dot { display: flex; align-items: center; gap: 0; }
.step-number { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0; background: var(--ink-surface); color: var(--text-dim); border: 1px solid var(--ink-border); transition: all var(--duration-normal) var(--ease-out); }
.step-dot.active .step-number { background: var(--amber); border-color: var(--amber); color: #fff; box-shadow: 0 0 12px var(--amber-glow); }
.step-dot.done .step-number { background: #3d3f48; border-color: #3d3f48; color: var(--text-muted); }
.step-label { margin-left: 8px; font-size: 12px; color: var(--text-dim); white-space: nowrap; transition: color var(--duration-normal) var(--ease-out); }
.step-dot.active .step-label { color: var(--amber-light); font-weight: 600; }
.step-dot.done .step-label { color: var(--text-muted); }
.step-line { width: 50px; height: 1px; background: var(--ink-border); margin: 0 16px; transition: background var(--duration-normal) var(--ease-out); }
.step-line.filled { background: #3d3f48; }

.step-content { min-height: 400px; }
.step-card { background: var(--ink-mid); border: 1px solid var(--ink-border); border-radius: var(--radius-xl); padding: var(--space-2xl); }
.card-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 8px; }
.card-number { font-family: var(--font-serif); font-size: 13px; font-weight: 700; color: var(--amber); letter-spacing: 1px; }
.card-title { font-family: var(--font-serif); font-size: 22px; font-weight: 700; color: var(--text-on-dark); }
.card-desc { color: var(--text-muted); font-size: 14px; margin-bottom: var(--space-xl); }
.card-desc strong { color: var(--amber-light); font-weight: 600; }
.card-actions { display: flex; gap: 12px; justify-content: flex-end; padding-top: var(--space-md); border-top: 1px solid var(--ink-border); }

.account-select-area { display: flex; flex-direction: column; gap: 8px; margin-bottom: var(--space-xl); }
.account-option { display: flex; align-items: center; gap: 14px; padding: 14px 18px; background: var(--ink-surface); border: 1px solid var(--ink-border); border-radius: var(--radius-lg); cursor: pointer; transition: all var(--duration-fast) var(--ease-out); position: relative; }
.account-option:hover { border-color: var(--text-dim); background: rgba(255,255,255,0.02); }
.account-option.selected { border-color: var(--amber); background: rgba(200,132,60,0.06); }
.account-avatar { width: 40px; height: 40px; border-radius: var(--radius-md); background: var(--amber-glow); color: var(--amber-light); display: flex; align-items: center; justify-content: center; font-family: var(--font-serif); font-size: 18px; font-weight: 700; flex-shrink: 0; }
.account-option.selected .account-avatar { background: var(--amber); color: #0c0e13; }
.account-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.account-name { font-size: 15px; font-weight: 600; color: var(--text-on-dark); }
.account-platform { font-size: 12px; color: var(--text-dim); }
.account-badge { font-size: 11px; padding: 3px 10px; border-radius: 20px; background: rgba(139,135,128,0.1); color: var(--text-dim); font-weight: 500; }
.account-badge.ready { background: rgba(91,140,90,0.12); color: var(--green-muted); }
.account-check { width: 22px; height: 22px; border-radius: 50%; background: var(--amber); color: #0c0e13; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }

.idea-input-area { margin-bottom: var(--space-xl); }
.idea-textarea { margin-bottom: 12px; }
.idea-hints { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.word-count-area { display: flex; align-items: center; gap: 12px; margin-bottom: var(--space-xl); padding: 12px 16px; background: var(--ink-card); border-radius: 8px; border: 1px solid var(--ink-border); }
.word-count-label { font-size: 14px; color: var(--text-muted); white-space: nowrap; }
.word-count-hint { font-size: 12px; color: var(--text-muted); white-space: nowrap; }
.hint-label { font-size: 12px; color: var(--text-dim); flex-shrink: 0; }
.hint-tag { font-size: 12px; padding: 4px 12px; border-radius: 20px; background: rgba(200,132,60,0.06); color: var(--text-muted); cursor: pointer; transition: all var(--duration-fast) var(--ease-out); border: 1px solid transparent; }
.hint-tag:hover { border-color: var(--amber); color: var(--amber-light); background: var(--amber-glow); }

/* 方向卡片 */
.directions-grid { display: flex; flex-direction: column; gap: 8px; margin-bottom: var(--space-xl); }
.direction-card { display: flex; align-items: center; gap: 14px; padding: 14px 18px; background: var(--ink-surface); border: 1px solid var(--ink-border); border-radius: var(--radius-lg); cursor: pointer; transition: all var(--duration-fast) var(--ease-out); }
.direction-card:hover { border-color: var(--text-dim); }
.direction-card.selected { border-color: var(--amber); background: rgba(200,132,60,0.06); }
.direction-id { font-family: var(--font-serif); font-size: 20px; font-weight: 700; color: var(--amber); width: 32px; flex-shrink: 0; }
.direction-title { flex: 1; font-size: 15px; color: var(--text-on-dark); }
.direction-check { color: var(--amber); font-weight: 700; }

/* 标题选择 */
.titles-grid { display: flex; flex-direction: column; gap: 8px; margin-bottom: var(--space-md); }
.title-card { display: flex; align-items: center; gap: 14px; padding: 14px 18px; background: var(--ink-surface); border: 1px solid var(--ink-border); border-radius: var(--radius-lg); cursor: pointer; transition: all var(--duration-fast) var(--ease-out); }
.title-card:hover { border-color: var(--text-dim); }
.title-card.selected { border-color: var(--amber); background: rgba(200,132,60,0.06); }
.title-id { font-family: var(--font-serif); font-size: 18px; font-weight: 700; color: var(--amber); width: 28px; flex-shrink: 0; }
.title-text { flex: 1; font-size: 15px; color: var(--text-on-dark); line-height: 1.5; }
.title-check { color: var(--amber); font-weight: 700; }
.title-edit-area { margin-bottom: var(--space-lg); }

/* 大纲列表 */
.outline-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: var(--space-md); }
.outline-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; }
.outline-order { width: 24px; height: 24px; border-radius: 50%; background: var(--amber-glow); color: var(--amber-light); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.outline-input { flex: 1; }

/* 生成中 */
.generating-state { text-align: center; padding: var(--space-2xl); }
.generating-spinner { width: 40px; height: 40px; border: 3px solid var(--ink-border); border-top-color: var(--amber); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px; }
@keyframes spin { to { transform: rotate(360deg); } }
.generating-text { color: var(--text-muted); font-size: 14px; }

/* 文章结果 */
.article-content { white-space: pre-wrap; line-height: 1.8; color: var(--text-on-dark); background: var(--ink-surface); padding: var(--space-xl); border-radius: var(--radius-lg); margin-bottom: var(--space-xl); font-size: 15px; max-height: 500px; overflow-y: auto; }
.loading-state { display: flex; align-items: center; gap: 12px; color: var(--text-muted); padding: var(--space-xl); justify-content: center; }

.step-trans-enter-active, .step-trans-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.step-trans-enter-from { opacity: 0; transform: translateX(20px); }
.step-trans-leave-to { opacity: 0; transform: translateX(-20px); }
</style>
