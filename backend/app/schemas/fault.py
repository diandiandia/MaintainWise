from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class FaultCreateRequest(BaseModel):
    equipment_id: int
    fault_title: str = Field(..., min_length=3, max_length=128)
    fault_desc: str = Field(..., min_length=5)
    fault_system: str = Field(..., description="ELECTRICAL, MECHANICAL, etc.")
    fault_part: str = Field(..., min_length=2, max_length=128)
    severity_level: str = Field(..., description="CRITICAL, MAJOR, MINOR")
    evidence_file_id: Optional[int] = None

class FaultResolveRequest(BaseModel):
    root_cause: str = Field(..., min_length=10, description="根本原因分析必填且至少10字")
    solution_steps: str = Field(..., min_length=10, description="解决步骤详细描述必填且至少10字")
    downtime_minutes: Optional[int] = 0
    is_featured_case: Optional[bool] = False

class SimilarCaseItem(BaseModel):
    article_id: int
    title: str
    match_score: float
    root_cause: str
    solution_steps: str
    is_featured: bool

class FaultResponse(BaseModel):
    id: int
    fault_code: str
    source_type: str
    equipment_id: int
    fault_title: str
    fault_desc: str
    fault_system: str
    fault_part: str
    severity_level: str
    status: str
    reported_by: int
    reported_at: datetime
    assigned_engineer_id: Optional[int] = None
    claimed_at: Optional[datetime] = None
    root_cause: Optional[str] = None
    solution_steps: Optional[str] = None
    downtime_minutes: int
    is_featured_case: bool
    is_sla_response_breached: bool
    is_sla_resolve_breached: bool

    model_config = ConfigDict(from_attributes=True)