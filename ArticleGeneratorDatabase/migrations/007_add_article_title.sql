-- 007_add_article_title.sql
-- 新增文章标题字段

ALTER TABLE articles ADD COLUMN title VARCHAR(200) COMMENT '文章标题';
