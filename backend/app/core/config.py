from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

# 动态解析项目工程根目录 (兼容 Linux 宿主机任意路径直接运行与 Docker 容器路径)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DEFAULT_UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow"
    )

    PROJECT_NAME: str = "MaintainWise 工厂设备维护管理系统"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 运行模式：linux_local (Linux宿主机直接测试/开发) | docker_production (Docker容器化集群部署)
    RUN_MODE: str = os.getenv("RUN_MODE", "linux_local")
    
    # 核心安全与 JWT 配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "maintainwise_super_secret_jwt_key_2026_change_me")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")) # 默认8小时(工业标准单班时长)
    
    # 数据库连接：
    # - Linux 宿主机直接测试：默认零依赖自动 fallback 到 sqlite:///./maintainwise.db (或内存数据库)
    # - Docker 生产部署：通过环境变量注入 postgresql://maintainwise:...@postgres:5432/maintainwise_db
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./maintainwise.db")
    
    # Redis 缓存与队列：
    # - Linux 宿主机直接测试：未启动 Redis 时自动降级为本地内存 MockRedis
    # - Docker 生产部署：通过环境变量注入 redis://:password@redis:6379/0
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 文件存储与上传限制：
    # - Linux 宿主机直接测试：自动定位至项目根目录 uploads/
    # - Docker 生产部署：通过环境变量指定 /app/uploads 并挂载 Docker 命名卷
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", DEFAULT_UPLOAD_DIR)
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    
    # 后台定时任务调度开关 (测试模式下默认关闭以防阻塞测试线程，Docker容器启动时开启)
    RUN_BACKGROUND_SCHEDULER: bool = os.getenv("RUN_BACKGROUND_SCHEDULER", "false").lower() in ("true", "1", "yes")

    # 默认超级管理员凭证
    DEFAULT_ADMIN_USERNAME: str = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "MaintainWiseAdmin@2026")
    DEFAULT_ADMIN_EMAIL: str = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@factory.com")
    DEFAULT_ADMIN_NAME: str = "系统超级管理员"
    DEFAULT_ADMIN_EMPLOYEE_NO: str = "EMP-ADMIN-001"

settings = Settings()
