-- 006_add_word_count_field.sql
-- 新增单个字数描述字段，替代 word_count_options + default_word_count 的 JSON 方案

ALTER TABLE accounts ADD COLUMN word_count TEXT COMMENT '字数描述，如：1500字左右、2000到3000字、3000字以上';
