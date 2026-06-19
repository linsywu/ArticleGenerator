CREATE TABLE IF NOT EXISTS collect_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    account_id INTEGER,
    start_time DATETIME,
    end_time DATETIME,
    total_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES collect_tasks(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_collect_logs_task ON collect_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_collect_logs_created ON collect_logs(created_at DESC);
