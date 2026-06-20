## ADDED Requirements

### Requirement: scenario_configs table has description and sort_order columns
The `scenario_configs` database table SHALL have `description` (TEXT) and `sort_order` (INTEGER DEFAULT 0) columns.

#### Scenario: Description and sort_order exist
- **WHEN** the migration is applied to the database
- **THEN** `PRAGMA table_info(scenario_configs)` includes `description` (TEXT) and `sort_order` (INTEGER)

### Requirement: ScenarioConfig Pydantic schemas declare description and sort_order
The `ScenarioConfigBase` Pydantic schema SHALL include `description` and `sort_order` as optional fields so they appear in API responses and are accepted in create/update requests.

#### Scenario: ScenarioConfigResponse includes description and sort_order
- **WHEN** `GET /api/scenario-configs` returns a list of configs
- **THEN** each config object includes `description` (string or null) and `sort_order` (integer)

#### Scenario: ScenarioConfigCreate accepts description and sort_order
- **WHEN** a POST request creates a new scenario config
- **THEN** the request body MAY include `description` and `sort_order`

#### Scenario: ScenarioConfigUpdate accepts description and sort_order
- **WHEN** a PUT request updates a scenario config
- **THEN** the request body MAY include `description` and `sort_order`

### Requirement: Seed data includes description and sort_order for all scenarios
The seed script SHALL populate `description` and `sort_order` for all seeded scenario configs.

#### Scenario: Existing seed scenarios get descriptions
- **WHEN** `scripts/seed_providers.py` runs
- **THEN** the `generate` scenario has `description = "⑤ 文章生成：根据热点/想法 + 风格画像 + 大纲生成全文"` and `sort_order = 5`
- **AND** the `refine` scenario has `description = "⑥ 微调重写：根据修改关键词调整文章风格/语气/侧重点"` and `sort_order = 6`
- **AND** the `distill` scenario has `description = "① 风格蒸馏：分析参考文章，提取7维度结构化风格画像"` and `sort_order = 1`
- **AND** the `quality_review` scenario has `description = "④ 质量评审：从原创性、逻辑、可读性、信息密度四个维度评分"` and `sort_order = 4`
- **AND** the `compliance_review` scenario has `description = "⑤ 合规评审：检查政治敏感、色情、暴力、虚假信息、侵权风险"` and `sort_order = 5"`

### Requirement: Frontend ScenarioConfig interface declares description and sort_order
The TypeScript `ScenarioConfig` interface SHALL include `description?: string` and `sort_order?: number`.

#### Scenario: ScenarioConfig type includes new fields
- **WHEN** `ScenarioConfigsView.vue` accesses `row.description` and `row.sort_order`
- **THEN** TypeScript type checking recognizes them as valid properties
