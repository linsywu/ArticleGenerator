-- 021: 新增 style_features 列
-- 存储蒸馏 Stage 1 的特征清单（带原文引证的证据），仅展示/审计用，不注入生成任务
ALTER TABLE accounts ADD COLUMN style_features TEXT;
