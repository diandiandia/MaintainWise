from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, BigInteger, JSON
from app.core.database import Base
from app.models.base import BaseAuditModel, utc_now

class User(BaseAuditModel):
    __tablename__ = "sys_users"

    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(64), nullable=False)
    employee_no = Column(String(32), unique=True, nullable=False, index=True)
    email = Column(String(128), nullable=False, index=True)
    phone = Column(String(32), nullable=True)
    role_code = Column(String(32), nullable=False, index=True) # ADMIN, ENGINEER, TECHNICIAN
    work_type = Column(String(32), nullable=False, index=True) # ELECTRICAL, MECHANICAL, AUTOMATION, GENERAL
    is_active = Column(Boolean, default=True, nullable=False)
    force_change_password = Column(Boolean, default=True, nullable=False)
    password_updated_at = Column(DateTime, default=utc_now, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = "sys_audit_logs"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id = Column(BigInteger().with_variant(Integer, "sqlite"), nullable=True)
    username = Column(String(64), nullable=True)
    client_ip = Column(String(45), nullable=False)
    module_name = Column(String(64), nullable=False, index=True)
    action_type = Column(String(32), nullable=False, index=True) # CREATE, UPDATE, DELETE, EXPORT
    request_url = Column(String(255), nullable=False)
    request_method = Column(String(10), nullable=False)
    diff_payload = Column(JSON, nullable=True)
    status_code = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
