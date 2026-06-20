## ADDED Requirements

### Requirement: humanize scenario config is seeded
The system SHALL include a `humanize` scenario config in the seed data so that the generate → humanize → review chain executes without silent failure.

#### Scenario: Seed script creates humanize config
- **WHEN** `scripts/seed_providers.py` is executed
- **THEN** a scenario_config row with `scenario = "humanize"` exists in the database
- **AND** the config has `description = "③ 去AI味：重写文章，消除AI写作痕迹，增加人味儿"`
- **AND** the config has `sort_order = 3`

### Requirement: direction, outline, and title scenario configs are seeded
The system SHALL include `direction`, `outline`, and `title` scenario configs in the seed data to support the full creation wizard.

#### Scenario: Seed script creates direction config
- **WHEN** `scripts/seed_providers.py` is executed
- **THEN** a scenario_config row with `scenario = "direction"` exists with `sort_order = 7`

#### Scenario: Seed script creates outline config
- **WHEN** `scripts/seed_providers.py` is executed
- **THEN** a scenario_config row with `scenario = "outline"` exists with `sort_order = 8`

#### Scenario: Seed script creates title config
- **WHEN** `scripts/seed_providers.py` is executed
- **THEN** a scenario_config row with `scenario = "title"` exists with `sort_order = 4`

### Requirement: Seed data is idempotent
The seed script SHALL NOT create duplicate scenario configs when run multiple times.

#### Scenario: Seed script rerun is safe
- **WHEN** `scripts/seed_providers.py` is executed a second time
- **THEN** no duplicate scenario_config rows are created
- **AND** existing rows are updated with current description and sort_order values
