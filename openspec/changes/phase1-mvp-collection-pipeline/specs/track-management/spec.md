## ADDED Requirements

### Requirement: User can manage first-level tracks
The system SHALL allow authenticated users to create, read, update, and delete first-level tracks (一级赛道). Each track MUST have a name, optional description, optional keywords list, optional forbidden keywords list, and a status flag (enabled/disabled).

#### Scenario: Create a new track
- **WHEN** user submits a track with name "AI科技" and description "AI行业资讯与深度分析"
- **THEN** system creates the track with status=enabled and returns the created track with id

#### Scenario: List all tracks
- **WHEN** user requests the track list
- **THEN** system returns all tracks ordered by created_at descending

#### Scenario: Filter tracks by status
- **WHEN** user requests tracks with status=enabled
- **THEN** system returns only enabled tracks

#### Scenario: Update a track
- **WHEN** user updates track name from "AI科技" to "人工智能"
- **THEN** system saves the change and returns the updated track

#### Scenario: Toggle track status
- **WHEN** user disables a track
- **THEN** system sets status=0 without deleting the record

#### Scenario: Delete a track cascades to sub-tracks
- **WHEN** user deletes a track that has associated sub-tracks
- **THEN** system removes the track and all its sub-tracks (cascade delete)

### Requirement: User can manage second-level sub-tracks
The system SHALL allow authenticated users to create, update, and delete second-level sub-tracks (二级赛道) under a parent track. Each sub-track MUST belong to exactly one first-level track.

#### Scenario: Add a sub-track to a track
- **WHEN** user adds a sub-track named "大模型" under track "AI科技"
- **THEN** system creates the sub-track associated with the parent track

#### Scenario: View sub-tracks with track details
- **WHEN** user views a track's details
- **THEN** system includes the list of all sub-tracks belonging to that track

#### Scenario: Delete a sub-track
- **WHEN** user deletes a sub-track
- **THEN** system removes the sub-track without affecting the parent track
