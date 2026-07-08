## ADDED Requirements

### Requirement: Direction card displays full quality check information
The direction card in the article creation flow SHALL display id, title, core_viewpoint, reader_gain, check, angle, and article_type in a hierarchical card layout.

#### Scenario: Direction card shows all fields
- **WHEN** the direction generation returns all 7 fields (`id`, `title`, `angle`, `core_viewpoint`, `reader_gain`, `article_type`, `check`)
- **THEN** the card displays: id badge + title (bold primary), core_viewpoint (gray secondary text), reader_gain (small text), check (smallest text), angle and article_type tags (colored, at bottom)

#### Scenario: Direction card gracefully handles missing fields
- **WHEN** the direction result contains only `id` and `title` (legacy format)
- **THEN** the card renders without errors, omitting missing field areas via `v-if`

### Requirement: Downstream steps use core_viewpoint
The outline, title, and article generation steps SHALL pass `core_viewpoint` (not `title`) as the `direction` parameter.

#### Scenario: Outline generation receives core_viewpoint
- **WHEN** user selects a direction and clicks "下一步 · 生成大纲"
- **THEN** the API call passes `selectedDirection.core_viewpoint` as the direction string

#### Scenario: Title generation receives core_viewpoint
- **WHEN** user proceeds to generate titles
- **THEN** the API call passes `selectedDirection.core_viewpoint` as the direction string

#### Scenario: Article generation receives core_viewpoint
- **WHEN** user triggers article generation
- **THEN** the API call passes `selectedDirection.core_viewpoint` as the direction string

#### Scenario: Step 4 displays core_viewpoint
- **WHEN** user is on the outline confirmation step
- **THEN** the display text shows `core_viewpoint` (not `title`) as the selected direction reference

#### Scenario: Fallback for legacy direction data
- **WHEN** a direction item has no `core_viewpoint` field (legacy data with only `id` and `title`)
- **THEN** the system falls back to using `title` as the direction parameter

### Requirement: DirectionItem schema supports extended fields
The `DirectionItem` Pydantic model and TypeScript interface SHALL include `angle`, `core_viewpoint`, `reader_gain`, `article_type`, and `check` as optional string fields.

#### Scenario: Backend accepts extended direction data
- **WHEN** the Celery task result contains all 7 fields
- **THEN** the API response preserves all fields without stripping

#### Scenario: Frontend type recognizes extended fields
- **WHEN** TypeScript code accesses `d.core_viewpoint`, `d.reader_gain`, `d.angle`, `d.article_type`, or `d.check`
- **THEN** no type error occurs
