## ADDED Requirements

### Requirement: MaterialsView has a creative direction dialog
The materials table in `MaterialsView.vue` SHALL open a creative direction generation dialog when the "💡 创作方向" button is clicked, replacing the placeholder `ElMessage.info`.

#### Scenario: Button opens direction dialog with material title
- **WHEN** user clicks "💡 创作方向" on a material row
- **THEN** a dialog opens titled "创作方向 - {material title}"
- **AND** the dialog begins calling `POST /api/generate/directions` with the material's title as `idea` and the material's `account_id`

#### Scenario: Loading state during generation
- **WHEN** the direction generation API has been called and is awaiting result
- **THEN** the dialog shows a loading spinner with text "正在生成创作方向..."
- **AND** the confirm/action buttons are disabled

#### Scenario: Directions displayed as selectable cards
- **WHEN** the generation completes successfully with 3-5 directions
- **THEN** each direction is displayed as a selectable card showing its `id` (e.g., "A") and `title`
- **AND** clicking a card selects it with a visual highlight (border color or background change)

#### Scenario: Generation timeout or failure
- **WHEN** the generation task does not complete within 60 seconds (30 polls × 2s) or returns an error
- **THEN** the dialog shows an error message "生成失败，请重试"
- **AND** a "重试" (retry) button is displayed

#### Scenario: User selects a direction and navigates to article creation
- **WHEN** user selects a direction card and clicks "去创作"
- **THEN** the dialog closes
- **AND** the router navigates to `/create?idea=<material_title>&direction=<selected_direction_title>&account_id=<account_id>`

### Requirement: MaterialsDirectionDialog component
The direction dialog SHALL be implemented as a separate Vue component `MaterialsDirectionDialog.vue`.

#### Scenario: Component props
- **WHEN** the parent MaterialsView uses the component
- **THEN** it passes `modelValue` (boolean, visibility), `material` (MpMaterial object), and emits `update:modelValue`

#### Scenario: Component manages its own generation state
- **WHEN** the dialog opens (modelValue becomes true)
- **THEN** the component calls the direction generation API internally
- **AND** manages loading/success/error state without parent involvement

### Requirement: CreateView reads query parameters for pre-fill
The `CreateView.vue` SHALL read `route.query` on mount to pre-fill the idea and direction fields.

#### Scenario: Pre-fill idea from query parameter
- **WHEN** CreateView mounts with `?idea=xxx` in the URL
- **THEN** the idea text input in Step 2 is pre-filled with the query value

#### Scenario: Pre-fill direction from query parameter
- **WHEN** CreateView mounts with `?direction=xxx` in the URL and the idea has been entered
- **THEN** after the directions are generated, the matching direction is pre-selected
