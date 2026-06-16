## ADDED Requirements

### Requirement: Reusable CRUD patterns
The system SHALL provide useCrudDialog hook for common create/update dialog logic used by ProvidersView, HotspotSourcesView, and ScenarioConfigsView.

#### Scenario: Code reduction
- **WHEN** comparing CRUD page code before and after refactoring
- **THEN** each of the three pages has at least 30% fewer lines
