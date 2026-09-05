from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, BigInteger, Text, ForeignKey
from app.core.database import Base
from app.models.base import BaseAuditModel, utc_now

class FaultRecord(BaseAuditModel):
    __tablename__ = "fault_records"

    fault_code = Column(String(64), unique=True, nullable=False, index=True)
    source_type = Column(String(32), nullable=False, index=True) # INSPECTION_AUTO, MANUAL_REPORT
    equipment_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipments.id"), nullable=False, index=True)
    snapshot_location_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipment_locations.id"), nullable=False)
    fault_title = Column(String(128), nullable=False)
    fault_desc = Column(Text, nullable=False)
    fault_system = Column(String(64), nullable=False, index=True) # ELECTRICAL, MECHANICAL, etc.
    fault_part = Column(String(128), nullable=False)
    severity_level = Column(String(32), nullable=False, index=True) # CRITICAL, MAJOR, MINOR
    status = Column(String(32), default="OPEN", nullable=False, index=True) # OPEN, IN_PROGRESS, RESOLVED_PENDING_REVIEW, RESOLVED, CLOSED, REOPENED
    
    reported_by = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("sys_users.id"), nullable=False, index=True)
    reported_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    
    assigned_engineer_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("sys_users.id"), nullable=True, index=True)
    claimed_at = Column(DateTime, nullable=True)
    
    root_cause = Column(Text, nullable=True)
    solution_steps = Column(Text, nullable=True)
    downtime_minutes = Column(Integer, default=0, nullable=False)
    is_featured_case = Column(Boolean, default=False, nullable=False, index=True)
    
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    is_sla_response_breached = Column(Boolean, default=False, nullable=False, index=True)
    is_sla_resolve_breached = Column(Boolean, default=False, nullable=False, index=True)

class SparePart(Base):
    __tablename__ = "fault_spare_parts"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    fault_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("fault_records.id", ondelete="CASCADE"), nullable=False, index=True)
    part_name = Column(String(128), nullable=False)
    part_model = Column(String(128), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit = Column(String(16), default="个", nullable=False)
