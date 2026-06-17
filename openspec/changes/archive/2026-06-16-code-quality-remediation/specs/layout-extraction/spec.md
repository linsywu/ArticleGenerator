## ADDED Requirements

### Requirement: Layout components
The system SHALL extract sidebar navigation and task center bell into dedicated layout components under components/layout/.

#### Scenario: AppSidebar component
- **WHEN** the application renders the navigation sidebar
- **THEN** it uses AppSidebar.vue from components/layout/

#### Scenario: TaskCenterBell component
- **WHEN** the application renders the task center indicator
- **THEN** it uses TaskCenterBell.vue from components/layout/

#### Scenario: App.vue is composition-focused
- **WHEN** reviewing App.vue
- **THEN** it primarily composes layout components rather than containing inline layout logic
