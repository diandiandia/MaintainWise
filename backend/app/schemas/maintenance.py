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
    plan_type: str = Field(..., description="DAILY, WEEKLY, MONTHLY, ANNUAL, HOURLY")
    interval_days: Optional[int] = Field(30, gt=0)
    interval_hours: Optional[int] = Field(None, gt=0, description="倒计时周期单位最小为小时")
    trigger_mode: Optional[str] = Field("CALENDAR", description="触发机制: CALENDAR / OPERATING_HOURS")
    advance_notice_days: Optional[int] = Field(3, gt=0, description="提前预警天数(日历模式)")
    advance_warning_hours: Optional[int] = Field(48, gt=0, description="提前预警工时数(工时模式)")
    sop_content: str = Field(..., min_length=5)
    equipment_ids: Optional[List[int]] = Field(default=[], description="关联设备ID列表")
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
    work_order_notes: Optional[str] = None # 技术员作业说明与工单编辑备注
    completion_proof_file_ids: Optional[List[int]] = None # 现场工作完成证据图片文件ID
    details: List[InspectionDetailSubmit]

class TaskClaimRequest(BaseModel):
    task_id: int

class TaskEditRequest(BaseModel):
    work_order_notes: Optional[str] = None
    completion_proof_file_ids: Optional[List[int]] = None

class TaskResponse(BaseModel):
    task_id: int
    task_code: str
    equipment_id: int
    equipment_name: str
    equipment_code: str
    scheduled_date: str
    due_date: str
    status: str
    is_overdue: bool
    assigned_tech_id: Optional[int] = None
    claimed_at: Optional[datetime] = None
    work_order_notes: Optional[str] = None
    completion_proof_file_ids: Optional[List[int]] = []

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