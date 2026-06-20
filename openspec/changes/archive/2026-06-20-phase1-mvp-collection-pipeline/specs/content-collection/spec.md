## ADDED Requirements

### Requirement: User can manage collection credentials
The system SHALL allow authenticated users to create, update, and delete WeChat MP collection credentials. Each credential MUST have a name, token, and cookie.

#### Scenario: Add a credential
- **WHEN** user submits name "主号凭证" with token and cookie values
- **THEN** system creates the credential with status="normal"

#### Scenario: Manual credential health check succeeds
- **WHEN** user triggers a check on a valid credential
- **THEN** system calls searchbiz with the credential, updates check_time, and keeps status="normal"

#### Scenario: Manual credential health check fails
- **WHEN** user triggers a check on an invalid credential
- **THEN** system updates status to "expired" and returns the failure reason

#### Scenario: Automated periodic health check
- **WHEN** the scheduled health check runs every 6 hours
- **THEN** system tests each credential and updates status accordingly

### Requirement: User can manage collection tasks with multi-level targeting
The system SHALL allow users to create collection tasks that target specific tracks and optionally specific accounts within those tracks.

#### Scenario: Create a task targeting an entire track
- **WHEN** user creates a task with track_ids=["1"] and account_ids=null
- **THEN** the task will collect from all accounts associated with track 1

#### Scenario: Create a task targeting specific accounts within a track
- **WHEN** user creates a task with track_ids=["1"] and account_ids=["5", "8"]
- **THEN** the task will only collect from accounts 5 and 8 (both must belong to track 1)

#### Scenario: Create a task with historical sync mode
- **WHEN** user creates a task with collect_mode="history_100"
- **THEN** the task will fetch the 100 most recent articles per account

#### Scenario: Create a task with incremental sync mode
- **WHEN** user creates a task with collect_mode="incremental"
- **THEN** the task will only fetch articles published after the account's last_collect_time

#### Scenario: Create a cron-scheduled task
- **WHEN** user creates a task with schedule_type="cron" and cron="0 9 * * *"
- **THEN** the task executes daily at 9:00 AM

### Requirement: Collection engine executes tasks with rate limiting
The system SHALL execute collection tasks with rate limiting designed to avoid WeChat platform anti-scraping detection.

#### Scenario: Collection respects global request interval
- **WHEN** the collector makes an HTTP request to WeChat MP API
- **THEN** at least 15 seconds (+ random jitter) pass before the next request from the same credential

#### Scenario: Collection skips recently collected accounts
- **WHEN** a task targets an account whose last_collect_time is less than 24 hours ago
- **THEN** the collector skips that account for this run

#### Scenario: Collection stops when credential is expired
- **WHEN** a task starts and its credential status is "expired"
- **THEN** the task aborts and logs an error

### Requirement: Collection engine deduplicates articles
The system SHALL prevent duplicate articles from being stored in mp_materials.

#### Scenario: URL dedup on insert
- **WHEN** the collector attempts to insert an article with an original_url that already exists
- **THEN** the insert is skipped due to the unique index on original_url

#### Scenario: Content hash dedup
- **WHEN** the collector encounters an article whose SHA256(raw_html) matches an existing content_hash
- **THEN** the article is skipped even if the URL differs

### Requirement: Collection engine retries failed article fetches
The system SHALL retry failed article fetches up to 3 times with increasing delays.

#### Scenario: First retry after 10 minutes
- **WHEN** an article fetch fails
- **THEN** the collector retries after 10 minutes

#### Scenario: Third and final retry after 60 minutes
- **WHEN** the first two retries fail
- **THEN** the collector makes a final attempt after 60 minutes, and if it fails, marks the article as failed

### Requirement: Collection engine writes execution logs
The system SHALL record a log entry for each collection task execution.

#### Scenario: Log records counts on success
- **WHEN** a collection task completes
- **THEN** a collect_log entry is written with task_id, account_id, total_count, success_count, fail_count, start_time, and end_time

#### Scenario: Log records errors on failure
- **WHEN** a collection task encounters errors
- **THEN** the collect_log entry includes error_message with details of each failed article
