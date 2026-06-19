CREATE TABLE IF NOT EXISTS mp_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    title VARCHAR(500),
    author VARCHAR(100),
    original_url VARCHAR(1000) NOT NULL,
    cover_url VARCHAR(500),
    summary TEXT,
    raw_html TEXT,
    content_markdown TEXT,
    content_hash VARCHAR(64),
    word_count INTEGER DEFAULT 0,
    is_original INTEGER DEFAULT 0,
    published_at DATETIME,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES mp_accounts(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_mp_materials_url ON mp_materials(original_url);
CREATE INDEX IF NOT EXISTS idx_mp_materials_account ON mp_materials(account_id);
CREATE INDEX IF NOT EXISTS idx_mp_materials_published ON mp_materials(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_mp_materials_hash ON mp_materials(content_hash);
