## ADDED Requirements

### Requirement: Remove step 6 dead code from CreateView
The system SHALL remove the unreachable step 6 template and submitForReview function from CreateView.vue.

#### Scenario: CreateView renders without step 6
- **WHEN** a user navigates through the article creation flow
- **THEN** only 5 valid steps are shown, no step 6 appears
- **AND** no submitForReview button is present

#### Scenario: No unreferenced reactive state
- **WHEN** running vue-tsc typecheck
- **THEN** no unreferenced ref or reactive variables exist in CreateView

### Requirement: Remove orphan page files
The system SHALL delete GenerateView.vue and DistillView.vue with zero residual references.

#### Scenario: Pages deleted
- **WHEN** checking the views directory
- **THEN** GenerateView.vue and DistillView.vue do not exist

#### Scenario: No residual imports
- **WHEN** searching the entire frontend source for GenerateView or DistillView imports
- **THEN** zero references are found

#### Scenario: Build succeeds
- **WHEN** running npm run build
- **THEN** the build completes without errors
