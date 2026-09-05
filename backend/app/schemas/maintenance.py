from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

class PlanItemCreateRequest(BaseModel):
    item_order: int = 1
    check_item_name: str = Field(..., min_length=2, max_length=128)
    standard_benchmark: str = Field(..., min_length=2)
    guide_image_id: Optional[int] = None
    is_required: bool = True

class MaintenancePlanCreateRequest(BaseModel):
    plan_code: str = Field(..., min_length=3, max_length=64)
    plan_name: str = Field(..., min_length=2, max_length=128)
    plan_type: str = Field(..., description="DAILY, WEEKLY, MONTHLY, ANNUAL")
    interval_days: int = Field(..., gt=0)
    sop_content: str = Field(..., min_length=5)
    items: List[PlanItemCreateRequest]

class InspectionDetailSubmit(BaseModel):
    plan_item_id: int
    check_item_name: str
    is_normal: bool
    anomaly_desc: Optional[str] = None
    evidence_file_id: Optional[int] = None

class InspectionSubmitRequest(BaseModel):
    task_id: Optional[int] = None
    equipment_id: int
    execution_start_time: datetime
    execution_end_time: Optional[datetime] = None
    overall_remarks: Optional[str] = None
    details: List[InspectionDetailSubmit]

class InspectionSubmitResponse(BaseModel):
    inspection_id: int
    has_anomaly: bool
    interlocked_fault_id: Optional[int] = None
    message: str

class CompletionRateItem(BaseModel):
    dimension_name: str
    total_due: int
    completed_on_time: int
    rate_percentage: float
