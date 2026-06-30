-- 017: generation_logs 添加 task_id + 完整提示词记录
ALTER TABLE generation_logs ADD COLUMN task_id VARCHAR(100) DEFAULT NULL;
ALTER TABLE generation_logs ADD COLUMN system_prompt TEXT DEFAULT NULL;
ALTER TABLE generation_logs ADD COLUMN user_prompt TEXT DEFAULT NULL;

-- generation_tasks 添加子任务关联，用于追踪 generate → humanize → review 链路
ALTER TABLE generation_tasks ADD COLUMN sub_task_ids TEXT DEFAULT NULL;
