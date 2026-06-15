-- 005_add_word_count_config.sql
-- 新增字数选项配置：word_count_options TEXT (JSON)，default_word_count VARCHAR(20)
-- SQLite 兼容版（不含 MySQL COMMENT 语法）

ALTER TABLE accounts ADD COLUMN word_count_options TEXT;
ALTER TABLE accounts ADD COLUMN default_word_count VARCHAR(20);
