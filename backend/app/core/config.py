from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow"
    )

    PROJECT_NAME: str = "MaintainWise 工厂设备维护管理系统"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 核心安全与 JWT 配置
    SECRET_KEY: str = "maintainwise_super_secret_jwt_key_2026_change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 数据库连接 (优先使用环境变量 DATABASE_URL，默认 fallback 到 sqlite)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./maintainwise.db")
    
    # Redis 缓存与队列连接
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 文件存储与上传限制
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/root/MaintainWise/uploads")
    MAX_UPLOAD_SIZE_MB: int = 50
    
    # 默认超级管理员凭证
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "MaintainWiseAdmin@2026"
    DEFAULT_ADMIN_EMAIL: str = "admin@factory.com"
    DEFAULT_ADMIN_NAME: str = "系统超级管理员"
    DEFAULT_ADMIN_EMPLOYEE_NO: str = "EMP-ADMIN-001"

settings = Settings()
