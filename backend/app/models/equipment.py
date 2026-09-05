from datetime import datetime, date
from sqlalchemy import Column, String, Boolean, DateTime, Date, Integer, BigInteger, Numeric, JSON, ForeignKey
from app.core.database import Base
from app.models.base import BaseAuditModel, utc_now

class Location(BaseAuditModel):
    __tablename__ = "equipment_locations"

    parent_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipment_locations.id"), nullable=True, index=True)
    location_name = Column(String(128), nullable=False)
    location_code = Column(String(64), unique=True, nullable=False, index=True)
    level_depth = Column(Integer, nullable=False) # 1 to 5 (1: FACTORY, 2: DEPARTMENT, 3: SYSTEM)
    node_type = Column(String(32), default="SYSTEM", nullable=False) # FACTORY, DEPARTMENT, SYSTEM
    tree_path = Column(String(255), nullable=False, index=True) # e.g. /1/2/3/
    is_leaf = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

class Equipment(BaseAuditModel):
    __tablename__ = "equipments"

    equipment_code = Column(String(64), unique=True, nullable=False, index=True)
    equipment_name = Column(String(128), nullable=False, index=True)
    equipment_type = Column(String(32), nullable=False, index=True) # SENSOR, PLC, FAN, MOTOR, INVERTER, etc.
    work_type = Column(String(32), nullable=False, index=True) # ELECTRICAL, MECHANICAL, AUTOMATION, GENERAL
    location_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipment_locations.id"), nullable=False, index=True)
    manufacturer = Column(String(128), nullable=True)
    model_spec = Column(String(128), nullable=False)
    serial_number = Column(String(128), nullable=True)
    purchase_date = Column(Date, nullable=True)
    commission_date = Column(Date, nullable=True)
    warranty_expiry_date = Column(Date, nullable=True)
    maintenance_interval_days = Column(Integer, default=30, nullable=False)
    maintenance_interval_hours = Column(Integer, default=720, nullable=False) # 最小周期单位小时
    next_maintenance_date = Column(Date, nullable=True, index=True)
    responsible_engineer_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("sys_users.id"), nullable=True)
    status = Column(String(32), default="RUNNING", nullable=False, index=True) # RUNNING, MAINTENANCE_PENDING, FAULTY, SHUTDOWN, SCRAPPED

class EquipmentParam(Base):
    __tablename__ = "equipment_params"

    equipment_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipments.id", ondelete="CASCADE"), primary_key=True)
    rated_power_kw = Column(Numeric(10, 2), nullable=True)
    rated_voltage_v = Column(Numeric(10, 2), nullable=True)
    rated_current_a = Column(Numeric(10, 2), nullable=True)
    rated_speed_rpm = Column(Integer, nullable=True)
    air_volume_m3h = Column(Numeric(10, 2), nullable=True)
    air_pressure_pa = Column(Numeric(10, 2), nullable=True)
    ip_address = Column(String(45), nullable=True)
    comm_protocol = Column(String(64), nullable=True)
    io_points_spec = Column(String(128), nullable=True)
    pressure_range_mpa = Column(Numeric(10, 2), nullable=True)
    measurement_range = Column(String(64), nullable=True)
    output_signal_type = Column(String(64), nullable=True)
    accuracy_class = Column(String(32), nullable=True)
    extra_params = Column(JSON, default=dict, nullable=False)

class EquipmentFile(Base):
    __tablename__ = "equipment_files"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    equipment_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipments.id", ondelete="SET NULL"), nullable=True, index=True)
    file_tag = Column(String(32), nullable=False, index=True) # PHOTO, NAMEPLATE, MANUAL, SCHEMATIC, PLC_PROG, FAULT_IMG, OTHER
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    file_size_bytes = Column(BigInteger().with_variant(Integer, "sqlite"), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_sha256 = Column(String(64), nullable=False)
    is_linked = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    created_by = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("sys_users.id"), nullable=True)
