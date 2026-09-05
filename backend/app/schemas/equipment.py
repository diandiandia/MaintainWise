from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import date, datetime

class LocationCreateRequest(BaseModel):
    parent_id: Optional[int] = None
    location_name: str = Field(..., min_length=2, max_length=128)
    location_code: str = Field(..., min_length=2, max_length=64)
    sort_order: Optional[int] = 0

class LocationResponse(BaseModel):
    id: int
    parent_id: Optional[int] = None
    location_name: str
    location_code: str
    level_depth: int
    tree_path: str
    is_leaf: bool
    sort_order: int
    children: Optional[List["LocationResponse"]] = []

    model_config = ConfigDict(from_attributes=True)

class EquipmentCreateRequest(BaseModel):
    equipment_code: str = Field(..., min_length=3, max_length=64)
    equipment_name: str = Field(..., min_length=2, max_length=128)
    equipment_type: str = Field(..., description="SENSOR, PLC, FAN, MOTOR, INVERTER, etc.")
    work_type: str = Field(..., description="ELECTRICAL, MECHANICAL, AUTOMATION, GENERAL")
    location_id: int
    manufacturer: Optional[str] = None
    model_spec: str = Field(..., min_length=2, max_length=128)
    serial_number: Optional[str] = None
    purchase_date: Optional[date] = None
    commission_date: Optional[date] = None
    warranty_expiry_date: Optional[date] = None
    maintenance_interval_days: Optional[int] = 30
    responsible_engineer_id: Optional[int] = None
    params: Optional[Dict[str, Any]] = None # 对应 11 类专有参数字典

class EquipmentUpdateRequest(BaseModel):
    equipment_name: Optional[str] = None
    location_id: Optional[int] = None
    manufacturer: Optional[str] = None
    model_spec: Optional[str] = None
    serial_number: Optional[str] = None
    maintenance_interval_days: Optional[int] = None
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
    next_maintenance_date: Optional[date] = None
    responsible_engineer_id: Optional[int] = None
    status: str
    created_at: datetime
    params: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class EquipmentTimelineItem(BaseModel):
    timestamp: datetime
    event_type: str # INSPECTION, FAULT, REPAIR
    title: str
    description: str
    operator_name: Optional[str] = None
    downtime_minutes: Optional[int] = 0
