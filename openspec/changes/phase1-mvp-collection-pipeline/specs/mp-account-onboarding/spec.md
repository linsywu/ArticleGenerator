## ADDED Requirements

### Requirement: User can manage MP accounts
The system SHALL allow authenticated users to create, read, update, and delete WeChat MP accounts (公众号). Each account MUST have a name and MAY have alias, fakeid, biz, avatar, description, and track associations.

#### Scenario: Create an MP account manually
- **WHEN** user submits an account with name "36氪" and track_ids ["1", "2"]
- **THEN** system creates the account with status=enabled

#### Scenario: List MP accounts with filters
- **WHEN** user requests account list filtered by track_id=1 and status=enabled
- **THEN** system returns only accounts matching both filters, paginated

#### Scenario: Search MP accounts by name
- **WHEN** user searches for "36"
- **THEN** system returns accounts whose name or alias contains "36"

#### Scenario: Update account track associations
- **WHEN** user updates an account's track_ids to ["2", "3"]
- **THEN** system saves the new track associations

#### Scenario: Toggle account status
- **WHEN** user disables an account
- **THEN** system sets status=0 and excludes it from future collection tasks

### Requirement: User can import MP accounts by name via searchbiz
The system SHALL allow users to submit a list of MP account names and automatically resolve them to account details using the WeChat searchbiz API.

#### Scenario: Import accounts by name
- **WHEN** user submits names ["36氪", "鸟哥笔记"] with a valid credential
- **THEN** system calls searchbiz for each name and creates mp_accounts with fetched fakeid, biz, avatar, and description

#### Scenario: Import fails when credential is expired
- **WHEN** user submits names with an expired credential
- **THEN** system returns an error indicating the credential is invalid

#### Scenario: Partial import success
- **WHEN** searchbiz finds "36氪" but not "不存在的公众号名"
- **THEN** system creates the found account and reports the unfound name

### Requirement: User can import MP accounts by article URL
The system SHALL allow users to submit article URLs and automatically extract biz parameter to identify the source account.

#### Scenario: Import account from article URL
- **WHEN** user submits a URL like "https://mp.weixin.qq.com/s/xxxx"
- **THEN** system extracts the biz parameter from the page, resolves account info, and creates the mp_account

#### Scenario: Import fails for invalid URL
- **WHEN** user submits a non-WeChat-article URL
- **THEN** system returns an error indicating the URL format is not recognized
