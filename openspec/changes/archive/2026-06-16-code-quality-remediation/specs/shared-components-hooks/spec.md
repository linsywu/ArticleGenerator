## ADDED Requirements

### Requirement: ArticleEditorDialog shared component
The system SHALL provide a single ArticleEditorDialog component used by ReviewView, PublishView, and CreateView for viewing/editing article content.

#### Scenario: Reused across views
- **WHEN** checking all article content dialog instances
- **THEN** they all use the same ArticleEditorDialog component

### Requirement: PageHeader component
The system SHALL provide a PageHeader component for consistent page title rendering across all list views.

#### Scenario: Consistent page headers
- **WHEN** navigating between list pages
- **THEN** all page titles use the PageHeader component

### Requirement: usePaginatedList hook
The system SHALL provide a usePaginatedList composable for reusable pagination + loading logic.

#### Scenario: Paginated list usage
- **WHEN** a list page needs pagination
- **THEN** it uses usePaginatedList hook instead of duplicating page/loading refs

### Requirement: App.vue under 250 lines
The system SHALL keep App.vue under 250 lines by extracting layout and bell logic to dedicated components.

#### Scenario: App.vue size
- **WHEN** checking App.vue line count
- **THEN** it is fewer than 250 lines
