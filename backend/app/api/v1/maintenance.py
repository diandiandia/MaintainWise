from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.user import User
from app.models.maintenance import MaintenancePlan, MaintenancePlanItem, MaintenanceTask, InspectionRecord
from app.models.equipment import Equipment
from app.schemas.maintenance import MaintenancePlanCreateRequest, InspectionSubmitRequest, InspectionSubmitResponse, CompletionRateItem
from app.schemas.common import BaseResponse, PageResult
from app.services.inspection_tx import InspectionAtomicService
from app.api.deps import get_current_user, require_role, check_fcp_status
from app.core.exceptions import BusinessException

router = APIRouter(prefix="/maintenance", tags=["维护与巡检"])

@router.get("/plans", response_model=BaseResponse)
def list_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status)
):
    plans = db.query(MaintenancePlan).filter(MaintenancePlan.is_deleted == False).all()
    results = []
    for p in plans:
        items = db.query(MaintenancePlanItem).filter(MaintenancePlanItem.plan_id == p.id).order_by(MaintenancePlanItem.item_order).all()
        results.append({
            "id": p.id,
            "plan_code": p.plan_code,
            "plan_name": p.plan_name,
            "plan_type": p.plan_type,
            "interval_days": p.interval_days,
            "version_no": p.version_no,
            "sop_content": p.sop_content,
            "items_count": len(items)
        })
    return BaseResponse(data=results)

@router.post("/plans", response_model=BaseResponse)
def create_plan(
    req: MaintenancePlanCreateRequest,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    plan = MaintenancePlan(
        plan_code=req.plan_code,
        plan_name=req.plan_name,
        plan_type=req.plan_type,
        interval_days=req.interval_days,
        version_no="V1.0",
        sop_content=req.sop_content,
        created_by=current_user.id
    )
    db.add(plan)
    db.flush()

    for item_req in req.items:
        item = MaintenancePlanItem(
            plan_id=plan.id,
            item_order=item_req.item_order,
            check_item_name=item_req.check_item_name,
            standard_benchmark=item_req.standard_benchmark,
            guide_image_id=item_req.guide_image_id,
            is_required=item_req.is_required
        )
        db.add(item)

    db.commit()
    return BaseResponse(data={"plan_id": plan.id}, message="维护计划及检查清单创建成功")

@router.get("/my-tasks", response_model=BaseResponse)
def get_my_tasks(
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    query = db.query(MaintenanceTask).filter(MaintenanceTask.status.in_(["PENDING", "OVERDUE"]))
    if current_user.role_code == "TECHNICIAN":
        query = query.filter(MaintenanceTask.assigned_tech_id == current_user.id)

    tasks = query.order_by(MaintenanceTask.due_date).all()
    results = []
    for t in tasks:
        eq = db.query(Equipment).filter(Equipment.id == t.equipment_id).first()
        results.append({
            "task_id": t.id,
            "task_code": t.task_code,
            "equipment_id": t.equipment_id,
            "equipment_name": eq.equipment_name if eq else "",
            "equipment_code": eq.equipment_code if eq else "",
            "scheduled_date": str(t.scheduled_date),
            "due_date": str(t.due_date),
            "status": t.status,
            "is_overdue": t.is_overdue
        })
    return BaseResponse(data=results)

@router.post("/inspections/submit", response_model=BaseResponse[InspectionSubmitResponse])
def submit_inspection(
    req: InspectionSubmitRequest,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    # 调用单事务原子提单服务
    result = InspectionAtomicService.submit_inspection(db, current_user.id, req.model_dump())
    return BaseResponse(
        data=InspectionSubmitResponse(
            inspection_id=result["inspection_id"],
            has_anomaly=result["has_anomaly"],
            interlocked_fault_id=result["interlocked_fault_id"],
            message=result["message"]
        ),
        message=result["message"]
    )

@router.get("/statistics/completion-rate", response_model=BaseResponse[List[CompletionRateItem]])
def get_completion_rate(
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    # 统计各设备类型的完成率
    total_tasks = db.query(MaintenanceTask).count()
    completed_tasks = db.query(MaintenanceTask).filter(MaintenanceTask.status == "COMPLETED").count()
    overall_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 100.0

    return BaseResponse(data=[
        CompletionRateItem(
            dimension_name="总体设备",
            total_due=total_tasks,
            completed_on_time=completed_tasks,
            rate_percentage=overall_rate
        )
    ])
