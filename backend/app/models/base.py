from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, Integer, Boolean, DateTime
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class BaseAuditModel(Base):
    """业务实体审计基础抽象模型"""
    __abstract__ = True

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    created_by = Column(BigInteger().with_variant(Integer, "sqlite"), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    updated_by = Column(BigInteger().with_variant(Integer, "sqlite"), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
