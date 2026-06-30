## ADDED Requirements

### Requirement: LLM receives user message with format instruction
The direction generation Celery task SHALL pass a `user_prompt` variable containing the idea, word count, optional style hints, and an explicit JSON format instruction.

#### Scenario: Direction generation with account style
- **WHEN** `trigger_direction_generation` is called with `account_id` > 0 and the account has `style_profile_structured`
- **THEN** the `user_prompt` variable SHALL include the idea, word count, thinking_pattern and structure_pattern as style hints, and a JSON format instruction

#### Scenario: Direction generation without account style
- **WHEN** `trigger_direction_generation` is called with `account_id` = 0 or an account without `style_profile_structured`
- **THEN** the `user_prompt` variable SHALL include the idea, word count, and JSON format instruction, with no style hints

### Requirement: Fallback parser supports Chinese numbering formats
The direction response parser SHALL recognize Chinese-numbered direction formats as alternatives to JSON output.

#### Scenario: Chinese format "方向一：title"
- **WHEN** the LLM response contains lines like `方向一：切入角度描述`
- **THEN** the parser SHALL extract each line as a direction with sequential letter IDs (A, B, C, D, E)

#### Scenario: Chinese format "角度1：title"
- **WHEN** the LLM response contains lines like `角度1：切入角度描述`
- **THEN** the parser SHALL extract each line as a direction with sequential letter IDs

#### Scenario: Bold markdown format "**A. title**"
- **WHEN** the LLM response contains `**A. 切入角度描述**` format
- **THEN** the parser SHALL extract each line as a direction, stripping the bold markers

### Requirement: Direction result is never silently empty on valid LLM response
The system SHALL return at least one direction whenever the LLM returns non-empty, non-error content.

#### Scenario: All parsers fail on non-empty content
- **WHEN** the LLM returns non-empty content that cannot be parsed by JSON, code-block, or pattern-based parsers
- **THEN** the system SHALL fall back to treating each non-empty line (up to 5) as a direction title
