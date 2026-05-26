-- 微调任务表（用于前端轮询微调完成状态）
CREATE TABLE IF NOT EXISTS refine_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL COMMENT 'Celery task_id',
    article_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/running/success/failed',
    error_message TEXT COMMENT '失败原因',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_task_id (task_id),
    INDEX idx_article (article_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='微调任务';
