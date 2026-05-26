-- 003_llm_gateway.sql
-- LLM网关改造：providers + scenario_configs + reference_articles + generation_logs
-- 同时扩展 accounts 和 articles 表

-- 1. API供应商表
CREATE TABLE IF NOT EXISTS providers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '供应商名称',
    base_url VARCHAR(500) NOT NULL COMMENT 'API地址',
    api_key VARCHAR(500) NOT NULL COMMENT 'API Key',
    models JSON COMMENT '可用模型列表',
    enabled TINYINT(1) DEFAULT 1 COMMENT '0否 1是',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API供应商';

-- 2. 场景路由配置表
CREATE TABLE IF NOT EXISTS scenario_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario VARCHAR(50) NOT NULL COMMENT 'distill/generate/quality_review/compliance_review/refine',
    provider_id INT NOT NULL,
    model VARCHAR(100) NOT NULL COMMENT '模型名',
    system_prompt_template TEXT COMMENT 'System Prompt模板',
    params JSON COMMENT 'temperature, max_tokens等',
    priority INT DEFAULT 0 COMMENT 'fallback顺序',
    enabled TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_scenario (scenario),
    FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='场景路由配置';

-- 3. 参考文章表
CREATE TABLE IF NOT EXISTS reference_articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    title VARCHAR(500) NOT NULL COMMENT '文章标题',
    content LONGTEXT NOT NULL COMMENT '正文',
    source_url VARCHAR(1000) COMMENT '来源链接',
    embedding JSON COMMENT 'embedding向量',
    is_benchmark TINYINT(1) DEFAULT 0 COMMENT '是否代表篇',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_account (account_id),
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='参考文章';

-- 4. 生成日志表
CREATE TABLE IF NOT EXISTS generation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario VARCHAR(50) NOT NULL,
    provider_id INT,
    model VARCHAR(100),
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    latency_ms INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_scenario (scenario),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生成日志';

-- 5. 扩展 accounts 表
ALTER TABLE accounts
    ADD COLUMN style_profile TEXT COMMENT '风格画像文本' AFTER sample_articles,
    ADD COLUMN style_profile_updated_at DATETIME COMMENT '画像更新时间' AFTER style_profile;

-- 6. 扩展 articles 表
ALTER TABLE articles
    ADD COLUMN quality_score INT COMMENT '质量评分 0-100' AFTER refine_history,
    ADD COLUMN compliance_score INT COMMENT '合规评分 0-100' AFTER quality_score,
    ADD COLUMN review_notes TEXT COMMENT '评审备注' AFTER compliance_score;
