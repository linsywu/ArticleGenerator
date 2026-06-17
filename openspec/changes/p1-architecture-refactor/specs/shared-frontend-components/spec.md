## ADDED Requirements

### Requirement: ArticleEditorDialog component
The system SHALL provide a single ArticleEditorDialog used by ReviewView, PublishView, and CreateView.

#### Scenario: Dialog reused across views
- **WHEN** checking article content editing in any view
- **THEN** the same ArticleEditorDialog component is used

### Requirement: PageHeader component
The system SHALL use PageHeader for consistent page titles across all list views.

### Requirement: usePaginatedList hook
The system SHALL provide a reusable composable for pagination + loading state.

### Requirement: useActiveTasks hook
The system SHALL provide a global singleton hook for active task polling.
