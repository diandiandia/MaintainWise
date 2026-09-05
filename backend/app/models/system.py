from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, BigInteger, ForeignKey
from app.core.database import Base
from app.models.base import utc_now

class SystemSmtpConfig(Base):
    __tablename__ = "sys_smtp_configs"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    smtp_host = Column(String(128), nullable=False)  # SMTP 主机，如 smtp.exmail.qq.com
    smtp_port = Column(Integer, default=465, nullable=False)  # 端口：465 (SSL), 587 (STARTTLS), 25
    smtp_user = Column(String(128), nullable=False)  # 发件账号 / 用户名
    smtp_pass = Column(String(255), nullable=False)  # 授权码 / 密码
    sender_name = Column(String(64), default="MaintainWise 智能运维中心", nullable=False)
    use_ssl = Column(Boolean, default=True, nullable=False)
    use_tls = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    updated_by = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("sys_users.id"), nullable=True)
