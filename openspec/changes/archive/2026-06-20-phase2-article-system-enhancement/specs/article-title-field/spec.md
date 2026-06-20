## ADDED Requirements

### Requirement: articles table has title column
The `articles` database table SHALL have a `title` column of type VARCHAR(200).

#### Scenario: Title column exists
- **WHEN** migration 007 is applied to the database
- **THEN** `PRAGMA table_info(articles)` includes a column named `title` with type VARCHAR(200)

### Requirement: Article Pydantic schemas declare title
The `ArticleBase` Pydantic schema SHALL include `title` as an optional field so that all Article response types inherit it.

#### Scenario: ArticleBase contains title
- **WHEN** a Pydantic schema inheriting from `ArticleBase` is used to serialize an article
- **THEN** the response JSON includes a `title` field
- **AND** the field is `null` when the article has no title (backward compatible)

### Requirement: Frontend Article interface declares title
The TypeScript `Article` interface in `src/api/types.ts` SHALL include `title?: string`.

#### Scenario: Article type includes title
- **WHEN** a view accesses `article.title`
- **THEN** TypeScript type checking recognizes it as `string | undefined`
- **AND** no type error is produced

### Requirement: Article title display uses direct field
Views displaying article titles SHALL use `article.title` as the primary display value, falling back to `hotspot.title` only when `title` is empty.

#### Scenario: Title displayed when present
- **WHEN** an article has a non-empty `title` field
- **THEN** the view displays `article.title` directly

#### Scenario: Fallback when title is absent
- **WHEN** an article's `title` is null or empty
- **THEN** the view falls back to `article.hotspot?.title || "-"`
