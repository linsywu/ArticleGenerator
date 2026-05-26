"""
应用配置，从环境变量读取
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 数据库：开发可用 sqlite，生产用 mysql
    database_url: str = "sqlite:///./article_generator.db"

    # Redis（Celery 消息队列）
    redis_url: str = "redis://localhost:6379/0"

    # 模型服务地址
    llm_service_url: str = "http://localhost:8001"

    # CORS
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
