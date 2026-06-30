-- 018: add custom_topic column to generation_tasks
-- 自定义主题任务没有 hotspot_id，需要 custom_topic 作为标题回退来源

ALTER TABLE generation_tasks ADD COLUMN custom_topic TEXT;
