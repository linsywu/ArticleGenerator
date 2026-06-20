## ADDED Requirements

### Requirement: User can browse collected materials with filters
The system SHALL allow users to browse collected mp_materials with filtering by track, account, date range, and keyword search.

#### Scenario: Filter materials by track
- **WHEN** user filters materials by track_id=1
- **THEN** system returns only materials from accounts associated with that track

#### Scenario: Filter materials by account
- **WHEN** user filters materials by account_id=5
- **THEN** system returns only materials from that specific account

#### Scenario: Filter materials by date range
- **WHEN** user filters materials with published_at between 2026-06-01 and 2026-06-30
- **THEN** system returns only materials published within that range

#### Scenario: Search materials by title
- **WHEN** user searches for "GPT"
- **THEN** system returns materials whose title contains "GPT", case-insensitive

### Requirement: User can view material details with lazy parsing
The system SHALL allow users to view a material's raw HTML and trigger Markdown conversion on demand.

#### Scenario: View raw HTML content
- **WHEN** user opens a material's detail page
- **THEN** system displays the raw_html content by default

#### Scenario: Trigger Markdown parsing on first access
- **WHEN** user switches to the Markdown tab and content_markdown is NULL
- **THEN** system converts raw_html to Markdown using Turndown, saves it to content_markdown, and displays the result

#### Scenario: Cached Markdown on subsequent access
- **WHEN** user switches to the Markdown tab and content_markdown already exists
- **THEN** system returns the cached Markdown immediately without re-parsing

### Requirement: Material list displays key metadata
The system SHALL display for each material in the list: track name, account name, title, word count, published date, and collection date.

#### Scenario: Material list shows computed track name
- **WHEN** materials are listed
- **THEN** each row shows the track name derived from the account's track_ids association

#### Scenario: Material list shows word count
- **WHEN** materials are listed
- **THEN** each row shows word_count (populated during collection from HTML text length estimation)
