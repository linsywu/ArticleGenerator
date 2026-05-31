-- 004_structured_style_profile.sql
-- 新增结构化风格画像字段
-- 7维度结构化画像：style_profile_structured TEXT (JSON)
-- 版本号：style_profile_version INTEGER DEFAULT 1
-- 状态：style_profile_status VARCHAR(20) DEFAULT 'none' (none/pending/ready/outdated)

ALTER TABLE accounts ADD COLUMN style_profile_structured TEXT COMMENT 'JSON: 7维度结构化画像（语气/句式/用词/结构/修辞/人称/互动风格）' AFTER style_profile_updated_at;
ALTER TABLE accounts ADD COLUMN style_profile_version INT DEFAULT 1 COMMENT '画像版本号' AFTER style_profile_structured;
ALTER TABLE accounts ADD COLUMN style_profile_status VARCHAR(20) DEFAULT 'none' COMMENT '画像状态: none/pending/ready/outdated' AFTER style_profile_version;
