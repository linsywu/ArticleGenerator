-- ArticleGenerator 数据库初始化脚本
-- 支持 MySQL 5.7+ / MariaDB 10.2+
-- 执行顺序：按文件名序号依次执行

-- 热点源配置表
CREATE TABLE IF NOT EXISTS hotspot_sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '源名称',
    type VARCHAR(50) NOT NULL COMMENT 'API/爬虫',
    config JSON COMMENT '配置（API Key、URL 等）',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用 0否 1是',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='热点源配置';

-- 账号风格表
CREATE TABLE IF NOT EXISTS accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    platform VARCHAR(50) NOT NULL COMMENT '平台（公众号/小红书等）',
    account_name VARCHAR(100) NOT NULL COMMENT '账号名',
    lora_path VARCHAR(500) DEFAULT NULL COMMENT 'LoRA 权重路径',
    sample_articles JSON COMMENT '示例文章（可选）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账号风格';

-- 热点表
CREATE TABLE IF NOT EXISTS hotspots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL COMMENT '热点标题',
    source VARCHAR(100) NOT NULL COMMENT '来源（微博/知乎/百度等）',
    heat INT DEFAULT 0 COMMENT '热度值',
    summary TEXT COMMENT '摘要',
    url VARCHAR(1000) DEFAULT NULL COMMENT '链接',
    status VARCHAR(20) DEFAULT 'unselected' COMMENT 'unselected/selected/generated',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_heat (heat DESC),
    INDEX idx_created_at (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='热点';

-- 文章表
CREATE TABLE IF NOT EXISTS articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hotspot_id INT NOT NULL COMMENT '关联热点',
    account_id INT NOT NULL COMMENT '关联账号',
    content LONGTEXT NOT NULL COMMENT '文章内容',
    status VARCHAR(20) DEFAULT 'pending_review' COMMENT 'pending_review/approved/rejected/published',
    refine_history JSON COMMENT '微调记录',
    published_at DATETIME DEFAULT NULL COMMENT '发布时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_hotspot (hotspot_id),
    INDEX idx_account (account_id),
    FOREIGN KEY (hotspot_id) REFERENCES hotspots(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文章';

-- 生成任务表（用于追踪 Celery 任务状态）
CREATE TABLE IF NOT EXISTS generation_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL COMMENT 'Celery task_id',
    hotspot_id INT NOT NULL,
    account_id INT NOT NULL,
    article_id INT DEFAULT NULL COMMENT '生成完成后关联文章',
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/running/success/failed',
    error_message TEXT COMMENT '失败原因',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_task_id (task_id),
    INDEX idx_status (status),
    FOREIGN KEY (hotspot_id) REFERENCES hotspots(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生成任务';
