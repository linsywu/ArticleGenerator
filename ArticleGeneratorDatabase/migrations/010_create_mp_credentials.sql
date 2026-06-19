CREATE TABLE IF NOT EXISTS mp_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    token VARCHAR(500) NOT NULL,
    cookie TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'normal',
    check_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mp_cred_status ON mp_credentials(status);
