"""
LLM 网关配置
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """网关配置——不再需要 MOCK_MODE 或 MODEL_PATH"""

    # 后端 API 地址（用于回查 providers / scenario_configs）
    backend_api_url: str = "http://localhost:8000"

    # 爬虫共享密钥（用于调用后端受保护 API）
    crawler_api_key: str = "crawler-dev-key"

    port: int = 8001

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
