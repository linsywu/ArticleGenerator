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
            <el-button size="large" :disabled="!selectedDirection" @click="skipToTitles">
              跳过大纲 · 直接生成标题
            </el-button>
            <el-button size="large" type="primary" :disabled="!selectedDirection" :loading="loadingOutline" @click="generateOutline">
              生成大纲预览
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
            <el-button size="large" @click="skipToTitles">不使用大纲 · 直接生成标题</el-button>
            <el-button size="large" type="primary" :disabled="!outline.length || !outline.every(o => o.point.trim())" @click="generateTitles">
              使用大纲 · 生成标题
            </el-button>
          </div>
        </div>

        <!-- 步骤 5: 生成标题 -->
        <div v-else-if="currentStep === 4" key="step5" class="step-card">
          <div class="card-header">
            <span class="card-number">05</span>
            <h2 class="card-title">选择文章标题</h2>
          </div>
          <p class="card-desc">方向：{{ selectedDirection?.title }}。从候选标题中选择或编辑。</p>
          <div v-if="titles.length" class="titles-grid">
            <div
              v-for="(t, i) in titles"
              :key="i"
              class="title-card"
              :class="{ selected: selectedTitle === t }"
              @click="selectedTitle = t; editedTitle = t"
            >
              <span class="title-index">{{ i + 1 }}</span>
              <span class="title-text">{{ t }}</span>
              <span v-if="selectedTitle === t" class="title-check">✓</span>
            </div>
          </div>
          <div v-if="titles.length" class="title-edit-area">
            <label class="title-edit-label">编辑选中标题</label>
            <el-input v-model="editedTitle" size="large" placeholder="编辑或自定义标题" />
          </div>
          <div v-else-if="loadingTitles" class="loading-state">
            <span>⏳ 正在生成标题...</span>
          </div>
          <div class="card-actions">
            <el-button size="large" @click="goBack()">返回上一步</el-button>
            <el-button
              size="large"
              type="primary"
              :disabled="!editedTitle.trim()"
              @click="currentStep = 5"
            >
              确认标题 · 生成全文
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
            <p class="generating-text">正在提交生成任务...</p>
          </div>
          <div v-else-if="taskSubmitted" class="task-submitted-state">
            <div class="submit-success-icon">✅</div>
            <p class="submit-title">文章生产中，请前往任务中心查看</p>
            <p class="submit-desc">文章生成需要一定时间，您可以在任务中心查看实时进度和结果。</p>
            <div class="card-actions">
              <el-button size="large" @click="goBack()">返回上一步</el-button>
              <el-button size="large" type="primary" @click="$router.push('/task-center')">前往任务中心</el-button>
            </div>
          </div>
          <div v-else class="card-actions">
            <el-button size="large" @click="goBack()">返回上一步</el-button>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import type { DirectionItem, OutlinePoint } from '@/api/client'
import { useAccountsStore } from "@/store/accounts"

const accountsStore = useAccountsStore()
const route = useRoute()

const steps = ['选择账号', '输入想法', '写作方向', '确认大纲', '生成标题', '生成全文']
const currentStep = ref(0)
const accounts = computed(() => accountsStore.accounts)
const selectedAccountId = ref<number | null>(null)
const idea = ref('')

// 步骤 3
const directions = ref<DirectionItem[]>([])
const selectedDirection = ref<DirectionItem | null>(null)
const loadingDirections = ref(false)

// 步骤 4
const outline = ref<OutlinePoint[]>([])
const loadingOutline = ref(false)

// 步骤 5
const generating = ref(false)
const taskSubmitted = ref(false)
// 步骤 5: 标题
const titles = ref<string[]>([])
const selectedTitle = ref('')
const editedTitle = ref('')
const loadingTitles = ref(false)
const selectedAccount = computed(() => accounts.value.find(a => a.id === selectedAccountId.value) || null)

async function generateDirections() {
  if (!selectedAccountId.value || !idea.value.trim()) return
  loadingDirections.value = true
  try {
    const { data } = await api.generateDirections(selectedAccountId.value, idea.value.trim())
    const taskId = data.task_id
    if (!taskId) throw new Error('未获取到任务 ID')

    // 轮询任务状态
    let attempts = 0
    const maxAttempts = 30
    while (attempts < maxAttempts) {
      await new Promise(r => setTimeout(r, 2000))
      const { data: taskData } = await api.getTaskResult(taskId)
      if (taskData.status === 'success') {
        const result = (taskData as any).result
        directions.value = result?.directions || []
        if (directions.value.length) {
          selectedDirection.value = directions.value[0]
          currentStep.value = 2
        }
        return
      }
      if (taskData.status === 'failed') throw new Error((taskData as any).error_message || '方向生成失败')
      attempts++
    }
    throw new Error('方向生成超时，请重试')
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '方向生成失败') }
  finally { loadingDirections.value = false }
}

async function generateOutline() {
  if (!selectedAccountId.value || !selectedDirection.value) return
  loadingOutline.value = true
  try {
    const { data } = await api.generateOutline(selectedAccountId.value, idea.value.trim(), selectedDirection.value.title)
    const taskId = data.task_id
    if (!taskId) throw new Error('未获取到任务 ID')

    // 轮询任务状态
    let attempts = 0
    const maxAttempts = 30
    while (attempts < maxAttempts) {
      await new Promise(r => setTimeout(r, 2000))
      const { data: taskData } = await api.getTaskResult(taskId)
      if (taskData.status === 'success') {
        const result = (taskData as any).result
        const rawOutline = result?.outline || []
        // 后端返回字符串数组，转为前端期望的 { order, point } 格式
        outline.value = rawOutline.map((item: any, i: number) =>
          typeof item === 'string' ? { order: i + 1, point: item } : item
        )
        if (outline.value.length) currentStep.value = 3
        return
      }
      if (taskData.status === 'failed') throw new Error((taskData as any).error_message || '大纲生成失败')
      attempts++
    }
    throw new Error('大纲生成超时，请重试')
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '大纲生成失败') }
  finally { loadingOutline.value = false }
}

function skipToTitles() {
  outline.value = []  // 清空大纲
  currentStep.value = 4  // 跳到标题生成步骤（step index 4），触发下方 watcher
}

// 统一返回上一步，正确处理跳过大纲的情况
function goBack() {
  if (currentStep.value === 4) {
    // 从标题步骤返回：如果跳过了大纲，回方向步骤；否则回大纲步骤
    currentStep.value = outline.value.length ? 3 : 2
  } else {
    currentStep.value = currentStep.value - 1
  }
}

// 进入步骤 5 时自动触发标题生成（仅 skip 路径；大纲路径已手动点击触发）
watch(currentStep, (step) => {
  if (step === 4 && !titles.value.length && !loadingTitles.value) {
    generateTitles()
  }
})

async function generateTitles() {
  if (!selectedAccountId.value || !selectedDirection.value) return
  loadingTitles.value = true
  try {
    const points = outline.value.length ? outline.value.map(o => o.point) : undefined
    const { data } = await api.generateTitles(selectedAccountId.value, idea.value.trim(), selectedDirection.value.title, points)
    const taskId = data.task_id
    if (!taskId) throw new Error('未获取到任务 ID')

    // 轮询任务状态
    let attempts = 0
    const maxAttempts = 30
    while (attempts < maxAttempts) {
      await new Promise(r => setTimeout(r, 2000))
      const { data: taskData } = await api.getTaskResult(taskId)
      if (taskData.status === 'success') {
        const result = (taskData as any).result
        titles.value = result?.titles || []
        if (titles.value.length) {
          selectedTitle.value = titles.value[0]
          editedTitle.value = titles.value[0]
          currentStep.value = 4
        }
        return
      }
      if (taskData.status === 'failed') throw new Error((taskData as any).error_message || '标题生成失败')
      attempts++
    }
    throw new Error('标题生成超时，请重试')
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || e?.message || '标题生成失败') }
  finally { loadingTitles.value = false }
}

function moveOutlineUp(i: number) { if (i > 0) { const t = outline.value[i]; outline.value[i] = outline.value[i-1]; outline.value[i-1] = t } }
function moveOutlineDown(i: number) { if (i < outline.value.length - 1) { const t = outline.value[i]; outline.value[i] = outline.value[i+1]; outline.value[i+1] = t } }

async function startGenerate() {
  if (!selectedAccountId.value || !idea.value.trim()) return
  generating.value = true
  currentStep.value = 5

  try {
    const points = outline.value.length ? outline.value.map(o => o.point) : undefined
    const topicWithTitle = editedTitle.value
      ? `${editedTitle.value}\n\n${idea.value.trim()}`
      : idea.value.trim()
    const { data } = await api.triggerGenerateWithOutline(selectedAccountId.value, topicWithTitle, points, undefined, selectedDirection.value?.title)
    const taskId = data.tasks?.[0]?.task_id
    if (!taskId) throw new Error('未获取到任务 ID')

    generating.value = false
    taskSubmitted.value = true
  } catch (e: any) {
    generating.value = false
    const errMsg = e?.response?.data?.detail || e?.message || '生成失败'
    try {
      await ElMessageBox.confirm(
        `文章生成失败：${errMsg}\n\n是否返回上一步重新尝试？`,
        '生成失败',
        { confirmButtonText: '返回上一步', cancelButtonText: '关闭', type: 'error' }
      )
      currentStep.value = outline.value.length ? 3 : 2
    } catch {
      // 用户点击关闭，留在当前页面
    }
  }
}

	// 进入步骤 6 时自动触发文章生成（仅首次进入）
	watch(currentStep, (step) => {
	  if (step === 5 && !generating.value && !taskSubmitted.value) {
	    startGenerate()
	  }
	})

	onMounted(async () => {
  try {
    await accountsStore.fetch()

    // Pre-fill from query params (from MaterialsView direction dialog)
    if (route.query.account_id) {
      const qAccountId = Number(route.query.account_id)
      if (!isNaN(qAccountId) && accounts.value.find(a => a.id === qAccountId)) {
        selectedAccountId.value = qAccountId
      }
    }
    if (!selectedAccountId.value && accounts.value.length) {
      selectedAccountId.value = accounts.value[0].id
    }

    // Pre-fill idea from query param (does NOT auto-generate directions)
    if (route.query.idea) {
      idea.value = String(route.query.idea)
    }

    // Auto-advance to step 1 when account is pre-filled from query (e.g., from materials center)
    if (route.query.account_id && selectedAccountId.value) {
      currentStep.value = 1
    }
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
.step-line { width: 56px; height: 1px; background: var(--ink-border); margin: 0 16px; transition: background var(--duration-normal) var(--ease-out); }
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

/* 标题卡片 */
.titles-grid { display: flex; flex-direction: column; gap: 8px; margin-bottom: var(--space-lg); }
.title-card { display: flex; align-items: center; gap: 12px; padding: 14px 18px; background: var(--ink-surface); border: 1px solid var(--ink-border); border-radius: var(--radius-lg); cursor: pointer; transition: all var(--duration-fast) var(--ease-out); }
.title-card:hover { border-color: var(--text-dim); }
.title-card.selected { border-color: var(--amber); background: rgba(200,132,60,0.06); }
.title-index { font-family: var(--font-serif); font-size: 16px; font-weight: 700; color: var(--amber); width: 24px; flex-shrink: 0; }
.title-text { flex: 1; font-size: 15px; color: var(--text-on-dark); }
.title-check { color: var(--amber); font-weight: 700; flex-shrink: 0; }
.title-edit-area { margin-bottom: var(--space-xl); }
.title-edit-label { display: block; font-size: 12px; color: var(--text-dim); margin-bottom: 6px; }

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

/* 任务提交成功 */
.task-submitted-state {
  text-align: center;
  padding: 40px 20px;
}
.submit-success-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.submit-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 8px 0;
}
.submit-desc {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin: 0 0 24px 0;
}

/* 文章结果 */
.article-content { white-space: pre-wrap; line-height: 1.8; color: var(--text-on-dark); background: var(--ink-surface); padding: var(--space-xl); border-radius: var(--radius-lg); margin-bottom: var(--space-xl); font-size: 15px; max-height: 500px; overflow-y: auto; }
.loading-state { display: flex; align-items: center; gap: 12px; color: var(--text-muted); padding: var(--space-xl); justify-content: center; }

.done-message { text-align: center; padding: var(--space-lg) 0; }
.done-title { font-size: 20px; font-weight: 700; color: var(--green-muted); margin-bottom: 6px; }
.done-desc { font-size: 14px; color: var(--text-muted); }

.step-trans-enter-active, .step-trans-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.step-trans-enter-from { opacity: 0; transform: translateX(20px); }
.step-trans-leave-to { opacity: 0; transform: translateX(-20px); }
</style>
