CREATE TABLE IF NOT EXISTS collect_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    credential_id INTEGER NOT NULL,
    track_ids TEXT,
    account_ids TEXT,
    collect_mode VARCHAR(30) NOT NULL DEFAULT 'incremental',
    date_start DATE,
    date_end DATE,
    schedule_type VARCHAR(20) DEFAULT 'manual',
    cron VARCHAR(50),
    interval_hours INTEGER,
    status VARCHAR(20) DEFAULT 'idle',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (credential_id) REFERENCES mp_credentials(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_collect_tasks_status ON collect_tasks(status);
