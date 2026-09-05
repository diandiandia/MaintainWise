from sqlalchemy import Column, String, Boolean, DateTime, Date, Integer, BigInteger, Text, ForeignKey, UniqueConstraint, JSON
from app.core.database import Base
from app.models.base import BaseAuditModel, utc_now

class MaintenancePlan(BaseAuditModel):
    __tablename__ = "maintenance_plans"

    plan_code = Column(String(64), unique=True, nullable=False, index=True)
    plan_name = Column(String(128), nullable=False)
    plan_type = Column(String(32), nullable=False) # DAILY, WEEKLY, MONTHLY, ANNUAL, HOURLY
    interval_days = Column(Integer, default=30, nullable=False)
    interval_hours = Column(Integer, default=720, nullable=False) # 倒计时周期单位最小为小时
    version_no = Column(String(16), default="V1.0", nullable=False)
    sop_content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    equipment_ids = Column(JSON, default=list, nullable=False) # 关联设备ID列表，支持多设备共用同一维护计划

class MaintenancePlanItem(Base):
    __tablename__ = "maintenance_plan_items"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    plan_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("maintenance_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    item_order = Column(Integer, default=1, nullable=False)
    check_item_name = Column(String(128), nullable=False)
    standard_benchmark = Column(Text, nullable=False)
    guide_image_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipment_files.id"), nullable=True)
    is_required = Column(Boolean, default=True, nullable=False)

class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    task_code = Column(String(64), unique=True, nullable=False, index=True)
    plan_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("maintenance_plans.id"), nullable=False)
    equipment_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipments.id"), nullable=False, index=True)
    assigned_tech_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("sys_users.id"), nullable=True)
    plan_version_snapshot = Column(String(16), default="V1.0", nullable=False)
    scheduled_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(String(32), default="PENDING", nullable=False, index=True) # PENDING, IN_PROGRESS, COMPLETED, OVERDUE
    completed_at = Column(DateTime, nullable=True)
    claimed_at = Column(DateTime, nullable=True) # 技术员接单时间
    work_order_notes = Column(Text, nullable=True) # 技术员工作执行与编辑说明
    completion_proof_file_ids = Column(JSON, default=list, nullable=False) # 现场工作完成证据图片文件ID列表
    is_overdue = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

class InspectionRecord(Base):
    __tablename__ = "inspection_records"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    task_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("maintenance_tasks.id"), nullable=True, index=True)
    equipment_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipments.id"), nullable=False, index=True)
    snapshot_location_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipment_locations.id"), nullable=False)
    inspector_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("sys_users.id"), nullable=False, index=True)
    has_anomaly = Column(Boolean, default=False, nullable=False, index=True)
    execution_start_time = Column(DateTime, nullable=False)
    execution_end_time = Column(DateTime, default=utc_now, nullable=False)
    overall_remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

class InspectionRecordDetail(Base):
    __tablename__ = "inspection_record_details"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    record_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("inspection_records.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_item_id = Column(BigInteger().with_variant(Integer, "sqlite"), nullable=False)
    check_item_name_snapshot = Column(String(128), nullable=False)
    is_normal = Column(Boolean, nullable=False)
    anomaly_desc = Column(Text, nullable=True)
    evidence_file_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipment_files.id"), nullable=True)
    interlocked_fault_id = Column(BigInteger().with_variant(Integer, "sqlite"), nullable=True)

class MaintenanceNotifyConfig(Base):
    __tablename__ = "maintenance_notify_configs"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    lead_days = Column(Integer, unique=True, nullable=False) # 7, 3, 1, 0
    is_enabled = Column(Boolean, default=True, nullable=False)
    target_role_group = Column(String(32), default="ALL", nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    updated_by = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("sys_users.id"), nullable=True)

class MaintenanceNotifyLog(Base):
    __tablename__ = "maintenance_notify_logs"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    equipment_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipments.id"), nullable=False, index=True)
    task_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("maintenance_tasks.id"), nullable=True)
    target_notify_date = Column(Date, nullable=False, index=True)
    notify_stage = Column(Integer, nullable=False) # 7, 3, 1, 0
    recipient_email = Column(String(128), nullable=False)
    sent_at = Column(DateTime, default=utc_now, nullable=False)
    status = Column(String(16), default="SUCCESS", nullable=False)

    __table_args__ = (
        UniqueConstraint("equipment_id", "target_notify_date", "notify_stage", "recipient_email", name="uq_maint_notify_dedup"),
    )