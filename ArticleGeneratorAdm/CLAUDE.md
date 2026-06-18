<!-- 加载顺序：AI agent 应先加载本文件，再加载 ../CLAUDE.md 获取全局约束 -->
<!-- 本文件中的内容为 ArticleGeneratorAdm 独有；全局约定见 ../CLAUDE.md -->

# ArticleGeneratorAdm — 管理后台前端

Vue 3 + Element Plus + Vite SPA，通过 Vite 代理 `/api` 到后端 `:8000`。

## 常用命令

### 启动

```bash
cd ArticleGeneratorAdm
npm install
npm run dev        # Vite dev server :5173，代理 /api → :8000
```

### 构建

```bash
npm run build      # esbuild 剥离类型不做检查
```

### 测试

```bash
npx vitest run
```

## 页面路由

| 路径 | 组件 | 用途 |
|------|------|------|
| `/login` | `LoginView` | 登录页 |
| `/` | `HotspotsView` | 热点列表、多选、批量生成 |
| `/create` | `CreateView` | 手动创建文章 |
| `/task-center` | `TaskCenterView` | 统一任务中心 |
| `/tasks` | `TasksView` | 生成任务状态、取消 |
| `/review` | `ReviewView` | 文章评审（通过/拒绝/微调） |
| `/publish` | `PublishView` | 待发布列表、复制、标记已发布 |
| `/hotspot-sources` | `HotspotSourcesView` | 热点源配置管理 |
| `/accounts` | `AccountsView` | 账号风格管理 |
| `/providers` | `ProvidersView` | API 供应商管理 |
| `/scenario-configs` | `ScenarioConfigsView` | 场景路由配置 |
| (layout) | `LayoutView` | 布局外壳（包裹所有页面，非独立路由） |

## 代码模式

以下模式为强制规范，新代码必须遵循。反模式代码会被要求重写。

### 组件分层

```
src/
├── components/        ← 共享组件（跨页面复用）
│   ├── PageHeader.vue          ✅ 通用页面头部
│   └── ArticleEditorDialog.vue ✅ 文章编辑器弹窗
├── views/             ← 页面壳（路由入口，只做编排，不写业务逻辑）
│   ├── HotspotsView.vue       ← 组装子组件 + 调用 API
│   └── AccountsView.vue
├── hooks/             ← 可复用业务逻辑
├── api/modules/       ← API 调用封装
├── store/             ← Pinia 状态管理
└── utils/             ← 纯工具函数
```

| 层级 | 职责 | 判断标准 |
|------|------|----------|
| `views/` | 页面壳：组装子组件、调用 API、管理页面级状态 | 能否在另一个页面直接复用？不能 → 属于 view 内部逻辑 |
| `components/` | 可跨页面复用的 UI 组件 | 是否在两个以上页面出现？是 → 提取到 components/ |
| `hooks/` | 可复用的状态/副作用逻辑 | 是否包含 `ref`/`reactive`/`onMounted` 且被多处使用？ |
| `api/modules/` | HTTP 请求封装 | 是否调用后端接口？是 → 必须在 api/modules/ 中封装 |

### 弹窗/对话框必须独立为组件

**❌ 反模式：在页面中内联弹窗代码**

```vue
<!-- views/SomeView.vue — 错！ -->
<template>
  <el-button @click="dialogVisible = true">打开</el-button>
  <el-dialog v-model="dialogVisible" title="新增" width="600px">
    <el-form :model="form"> ... 大量表单项 ... </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确认</el-button>
    </template>
  </el-dialog>
</template>
```

问题：页面文件臃肿（当前 `AccountsView.vue` 614 行）、弹窗逻辑无法复用、单文件职责不清。

**✅ 正确：弹窗抽离为独立组件**

```vue
<!-- components/AccountCreateDialog.vue -->
<script setup lang="ts">
import { ref, defineEmits } from 'vue'
import { createAccount } from '@/api/modules/accounts'
import type { AccountCreate } from '@/api/types'

const emit = defineEmits<{ success: [] }>()
const visible = ref(false)
const form = ref<AccountCreate>({ account_name: '', platform: '' })

const open = () => { visible.value = true }
const handleSubmit = async () => {
  await createAccount(form.value)
  visible.value = false
  emit('success')
}
defineExpose({ open })
</script>

<template>
  <el-dialog v-model="visible" title="新增账号" width="600px">
    <el-form :model="form"> ... </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确认</el-button>
    </template>
  </el-dialog>
</template>
```

```vue
<!-- views/SomeView.vue — 页面只做编排 -->
<script setup lang="ts">
import { ref } from 'vue'
import AccountCreateDialog from '@/components/AccountCreateDialog.vue'

const dialogRef = ref<InstanceType<typeof AccountCreateDialog>>()
</script>

<template>
  <el-button @click="dialogRef?.open()">新增</el-button>
  <AccountCreateDialog ref="dialogRef" @success="refreshList" />
</template>
```

**弹窗组件规范**：
- 放在 `components/`，命名以 `Dialog.vue` 结尾
- 通过 `defineExpose({ open })` 暴露打开方法
- 通过 `emit('success')` 通知父组件刷新
- 弹窗内部自己管理表单状态和提交逻辑

### API 调用必须通过 client 封装

**❌ 反模式**
```ts
// 组件中直接 fetch
const res = await fetch('/api/accounts')
const data = await res.json()
```

**✅ 正确**
```ts
// api/modules/accounts.ts
import client from '../client'
import type { Account, AccountCreate } from '../types'

export const getAccounts = () => client.get<Account[]>('/api/accounts')
export const createAccount = (data: AccountCreate) => client.post<Account>('/api/accounts', data)
```

详见 `src/api/client.ts` + `src/api/types.ts` + `src/api/modules/*.ts` + `src/api/index.ts`。

### 新增页面的标准步骤

1. 如果需要新弹窗 → `components/XxxDialog.vue` 创建弹窗组件
2. 如果需要新 API → `api/types.ts` 加类型 + `api/modules/xxx.ts` 加方法 + `api/index.ts` 导出
3. `views/XxxView.vue` 创建页面壳（组装组件 + 调 API）
4. `router/index.ts` 注册路由
5. 启动 `npm run dev`，浏览器验证控制台无报错

## 代码约定

- 页面逻辑抽离为 `components/` 子组件
- 公用工具：`utils/`、`api/`、`store/`
- 业务 hooks：`hooks/`
- API client 结构：`client.ts` + `types.ts` + `modules/*.ts` + `index.ts`
- **弹窗必须独立为 `components/XxxDialog.vue`，禁止在 views 中内联** `el-dialog`
- **单文件不超过 300 行**，超过则必须拆分

## 已知陷阱

### 前端验证铁律（不可绕过）

**前端代码变更后，禁止仅依赖 `npm run build` + `npm run test` 通过即声称验证完成。** 必须执行：

1. 启动 Vite dev server（`npm run dev`）
2. 浏览器访问受影响的页面，打开控制台
3. 确认无 `Uncaught TypeError`、`is not a function` 等运行时错误
4. 走通关键操作流程

**原因**：`npm run build` 使用 esbuild 剥离类型不做检查；App.vue 级运行时逻辑无测试覆盖。历史上 `api.getUnifiedTasks is not a function` 在 build+test 全绿时未被发现，根因是 worktree base 落后 main 导致重构丢失新增方法。

### 组件测试限制
jsdom 不支持 Vue SFC 的动态 `import()`，会导致 `InvalidCharacterError`。组件级测试需改为浏览器手动验证。API client 和纯 JS/TS 模块测试正常。

### Vite 代理
前端请求 `/api/*` 通过 Vite 代理转发到后端 `:8000`。开发时确保后端已在 `:8000` 运行，否则 API 请求返回 404。
