-- 020: 移除 style_profile_structured 列
-- 蒸馏重构后不再使用 7 维度结构化画像，风格指南整段存于 style_profile
-- 注意：SQLite 3.35.0+ 支持 ALTER TABLE DROP COLUMN

ALTER TABLE accounts DROP COLUMN style_profile_structured;
