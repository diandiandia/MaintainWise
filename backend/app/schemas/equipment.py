from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import date, datetime

class LocationCreateRequest(BaseModel):
    parent_id: Optional[int] = None
    location_name: str = Field(..., min_length=2, max_length=128)
    location_code: str = Field(..., min_length=2, max_length=64)
    node_type: Optional[str] = None # FACTORY, DEPARTMENT, SYSTEM
    sort_order: Optional[int] = 0

class LocationResponse(BaseModel):
    id: Any
    parent_id: Optional[Any] = None
    location_name: str
    location_code: str
    level_depth: int
    node_type: Optional[str] = "SYSTEM" # FACTORY, DEPARTMENT, SYSTEM, EQUIPMENT
    tree_path: Optional[str] = ""
    is_leaf: bool
    sort_order: int
    equipment_id: Optional[int] = None
    children: Optional[List["LocationResponse"]] = []

    model_config = ConfigDict(from_attributes=True)

class EquipmentCreateRequest(BaseModel):
    equipment_code: str = Field(..., min_length=3, max_length=64)
    equipment_name: str = Field(..., min_length=2, max_length=128)
    equipment_type: str = Field(..., description="SENSOR, PLC, FAN, MOTOR, INVERTER, etc.")
    work_type: Optional[str] = Field("GENERAL", description="ELECTRICAL, MECHANICAL, AUTOMATION, GENERAL")
    location_id: int
    manufacturer: Optional[str] = None
    model_spec: str = Field(..., min_length=2, max_length=128)
    serial_number: Optional[str] = None
    purchase_date: Optional[date] = None
    commission_date: Optional[date] = None
    warranty_expiry_date: Optional[date] = None
    maintenance_interval_days: Optional[int] = 30
    maintenance_interval_hours: Optional[int] = 720 # 最小倒计时周期为小时
    responsible_engineer_id: Optional[int] = None
    params: Optional[Dict[str, Any]] = None # 对应 11 类专有参数字典

class EquipmentUpdateRequest(BaseModel):
    equipment_name: Optional[str] = None
    location_id: Optional[int] = None
    manufacturer: Optional[str] = None
    model_spec: Optional[str] = None
    serial_number: Optional[str] = None
    maintenance_interval_days: Optional[int] = None
    maintenance_interval_hours: Optional[int] = None
    responsible_engineer_id: Optional[int] = None
    status: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

class EquipmentResponse(BaseModel):
    id: int
    equipment_code: str
    equipment_name: str
    equipment_type: str
    work_type: str
    location_id: int
    manufacturer: Optional[str] = None
    model_spec: str
    serial_number: Optional[str] = None
    maintenance_interval_days: int
    maintenance_interval_hours: Optional[int] = 720
    next_maintenance_date: Optional[date] = None
    responsible_engineer_id: Optional[int] = None
    status: str
    current_operating_hours: Optional[float] = 0.0
    created_at: datetime
    params: Optional[Dict[str, Any]] = None
    location_path: Optional[str] = None
    location_name_display: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class EquipmentTimelineItem(BaseModel):
    timestamp: datetime
    event_type: str # INSPECTION, FAULT, REPAIR
    title: str
    description: str
    operator_name: Optional[str] = None
    downtime_minutes: Optional[int] = 0

class EquipmentOperatingLogCreateRequest(BaseModel):
    equipment_id: Optional[int] = None
    log_date: Optional[date] = None # 默认为当天
    duration_hours: float = Field(..., gt=0, le=24.0, description="当日运行小时数 (0 < x <= 24)")
    proof_image_id: Optional[int] = None
    remarks: Optional[str] = None

class EquipmentOperatingLogResponse(BaseModel):
    id: int
    equipment_id: int
    log_date: date
    duration_hours: float
    cumulative_hours: float
    proof_image_id: Optional[int] = None
    operator_id: int
    operator_name: Optional[str] = None
    remarks: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EquipmentOperatingSummary(BaseModel):
    equipment_id: int
    equipment_code: str
    equipment_name: str
    current_operating_hours: float
    interval_hours: int
    advance_warning_hours: int
    remaining_hours: float
    progress_percentage: float
    is_warning: bool
    is_due: bool
    status: str
    last_log_date: Optional[date] = None