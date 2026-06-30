## ADDED Requirements

### Requirement: Outline step is optional in creation flow
前端文章创建流程中，大纲生成步骤 SHALL 为可选步骤，默认不执行。

#### Scenario: User skips outline generation
- **WHEN** 用户在标题生成后直接点击"生成全文"
- **THEN** 系统 SHALL 跳过调用 `/generate/outline`，直接触发 `/generate/trigger`，`outline` 参数为空数组或不传

#### Scenario: User opt-in to outline
- **WHEN** 用户主动点击"生成大纲预览"
- **THEN** 系统 SHALL 调用 `/generate/outline` 生成大纲并展示，确认后 `outline` 参数随 `/generate/trigger` 一起发送

### Requirement: Backend handles empty outline gracefully
后端生成逻辑 SHALL 支持无大纲模式。当 `outline` 为空或未传时，`outline_section` SHALL 渲染为空字符串，不在最终 prompt 中残留空标题或未闭合 section。

#### Scenario: Generate without outline
- **WHEN** `trigger_generate` 收到 `outline=None` 或 `outline=[]`
- **THEN** `outline_section` SHALL 为 `""`，System Prompt 中不出现大纲相关指令

#### Scenario: Generate with outline
- **WHEN** `trigger_generate` 收到非空 `outline` 列表
- **THEN** `outline_section` SHALL 包含 `## 写作大纲` 标题、编号列表和 `请严格按照以上大纲逐段写作。` 约束语

### Requirement: Frontend flow reflects optional outline
CreateView.vue 的步骤编排 SHALL 将大纲步骤标记为可选，UI 上区分"跳过"和"生成大纲"两个操作。

#### Scenario: Outline step UI
- **WHEN** 用户完成标题编辑步骤
- **THEN** 界面 SHALL 同时展示"跳过，直接生成全文"和"生成大纲预览"两个按钮
