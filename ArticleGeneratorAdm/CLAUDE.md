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
| `/` | `HotspotsView` | 热点列表、多选、批量生成 |
| `/tasks` | `TasksView` | 生成任务状态、取消 |
| `/review` | `ReviewView` | 文章评审（通过/拒绝/微调） |
| `/publish` | `PublishView` | 待发布列表、复制、标记已发布 |
| `/hotspot-sources` | `HotspotSourcesView` | 热点源配置管理 |
| `/accounts` | `AccountsView` | 账号风格管理 |

## 代码约定

- 页面逻辑抽离为 `components/` 子组件
- 公用工具：`utils/`、`api/`、`store/`
- 业务 hooks：`hooks/`
- API client 结构：`client.ts` + `types.ts` + `modules/*.ts` + `index.ts`

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
