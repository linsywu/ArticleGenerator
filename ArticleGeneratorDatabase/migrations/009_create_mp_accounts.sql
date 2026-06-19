CREATE TABLE IF NOT EXISTS mp_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    alias VARCHAR(100),
    fakeid VARCHAR(100),
    biz VARCHAR(100),
    avatar VARCHAR(500),
    description TEXT,
    track_ids TEXT,
    article_count INTEGER DEFAULT 0,
    last_collect_time DATETIME,
    status INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mp_accounts_status ON mp_accounts(status);
CREATE INDEX IF NOT EXISTS idx_mp_accounts_fakeid ON mp_accounts(fakeid);
