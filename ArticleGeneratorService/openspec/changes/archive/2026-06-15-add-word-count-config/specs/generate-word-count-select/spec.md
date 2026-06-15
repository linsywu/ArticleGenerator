## ADDED Requirements

### Requirement: Word count selector in creation flow
The system SHALL display a word count selector in step 2 (输入想法) of the article creation flow when the selected account has word count options configured. The selector SHALL default to the account's default word count. If not selected, the account's default SHALL be used.

#### Scenario: Word count selector visible when options exist
- **WHEN** the user navigates to step 2 (输入想法) and the selected account has `word_count_options` configured
- **THEN** a word count dropdown selector SHALL be visible alongside the idea input area

#### Scenario: Word count selector hidden when no options
- **WHEN** the user navigates to step 2 and the selected account has no `word_count_options`
- **THEN** no word count selector SHALL be displayed

#### Scenario: Default word count pre-selected
- **WHEN** the user navigates to step 2 and the account has `default_word_count = "1500"`
- **THEN** the word count selector SHALL show "1500" as the pre-selected value

#### Scenario: User overrides word count
- **WHEN** the user changes the word count selector from "1500" to "3000" and proceeds to generate
- **THEN** the generation request SHALL include `word_count = "3000"` and the LLM prompt SHALL reflect "3000字"

#### Scenario: Word count injected into generation prompt
- **WHEN** a generation task receives `word_count = "1500左右"`
- **THEN** the LLM prompt SHALL include the word count instruction (e.g., "字数1500左右。")

#### Scenario: Fallback when word count not provided
- **WHEN** a generation task receives no `word_count` (legacy flow or not selected)
- **THEN** the task SHALL use the current hardcoded default "1500左右" as fallback
