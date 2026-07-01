## ADDED Requirements

### Requirement: Generate prompt uses only style_profile for style guidance

The `generate` scenario's `system_prompt_template` SHALL reference `{{style_profile}}` as the sole source of writing style guidance. The `{{style_instructions}}` placeholder SHALL be removed from the template.

#### Scenario: Template has no style_instructions placeholder
- **WHEN** the generate scenario config is loaded
- **THEN** the `system_prompt_template` does NOT contain `{{style_instructions}}`

#### Scenario: Template has style_profile as writing requirement
- **WHEN** the generate scenario config is loaded
- **THEN** the `system_prompt_template` contains `{{style_profile}}` with surrounding text that frames it as a mandatory style requirement (e.g., "写作风格要求（必须严格遵守）")

### Requirement: trigger_generate does not build or pass style_instructions

The `trigger_generate` Celery task in `tasks.py` SHALL NOT construct a `style_instructions` string, and SHALL NOT include `style_instructions` in the `variables` dict passed to the LLM `/chat` endpoint.

#### Scenario: variables dict excludes style_instructions
- **WHEN** `trigger_generate` executes and builds the `/chat` payload
- **THEN** the `variables` dict contains `style_profile` (via Gateway auto-injection) but does NOT contain `style_instructions`

#### Scenario: No style_instructions construction code
- **WHEN** reviewing `trigger_generate` source code
- **THEN** there is no code that reads `account.style_profile_structured` and formats it into a `style_instructions` string

### Requirement: Frontend variable documentation updated

The `ScenarioConfigsView.vue` component SHALL remove the `style_instructions` entry from the generate scenario's variable hints list.

#### Scenario: Variable hints list excludes style_instructions
- **WHEN** the ScenarioConfigsView is rendered for the generate scenario
- **THEN** the variable hints section does NOT display `style_instructions` as an available variable
