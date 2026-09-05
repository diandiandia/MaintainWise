import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import io
from app.core.database import get_db
from app.models.user import User
from app.models.maintenance import MaintenancePlan, MaintenancePlanItem, MaintenanceTask, InspectionRecord
from app.models.equipment import Equipment
from app.schemas.maintenance import (
    MaintenancePlanCreateRequest,
    InspectionSubmitRequest,
    InspectionSubmitResponse,
    CompletionRateItem,
    TaskClaimRequest,
    TaskEditRequest
)
from app.schemas.common import BaseResponse, PageResult
from app.services.inspection_tx import InspectionAtomicService
from app.services.excel_processor import ExcelProcessor
from app.api.deps import get_current_user, require_role, check_fcp_status
from app.core.exceptions import BusinessException

router = APIRouter(prefix="/maintenance", tags=["设备维护"])

@router.get("/plans", response_model=BaseResponse)
def list_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status)
):
    plans = db.query(MaintenancePlan).filter(MaintenancePlan.is_deleted == False).order_by(MaintenancePlan.id.desc()).all()
    results = []
    for p in plans:
        items = db.query(MaintenancePlanItem).filter(MaintenancePlanItem.plan_id == p.id).order_by(MaintenancePlanItem.item_order).all()
        adv_days = getattr(p, "advance_notice_days", None)
        if adv_days is None:
            adv_hours = getattr(p, "advance_warning_hours", 48) or 48
            adv_days = max(1, round(adv_hours / 24.0))

        results.append({
            "id": p.id,
            "plan_code": p.plan_code,
            "plan_name": p.plan_name,
            "plan_type": p.plan_type,
            "trigger_mode": getattr(p, "trigger_mode", "CALENDAR") or "CALENDAR",
            "interval_days": p.interval_days,
            "interval_hours": getattr(p, "interval_hours", p.interval_days * 24),
            "advance_notice_days": adv_days,
            "advance_warning_hours": getattr(p, "advance_warning_hours", 48) or 48,
            "version_no": p.version_no,
            "sop_content": p.sop_content,
            "is_active": getattr(p, "is_active", True),
            "equipment_ids": getattr(p, "equipment_ids", []),
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
    interval_hours = req.interval_hours or (req.interval_days * 24 if req.interval_days else 720)
    interval_days = max(1, interval_hours // 24)
    trigger_mode = req.trigger_mode or "CALENDAR"

    if trigger_mode == "CALENDAR":
        advance_notice_days = req.advance_notice_days if req.advance_notice_days is not None else 3
        advance_warning_hours = req.advance_warning_hours or (advance_notice_days * 24)
    else:
        advance_warning_hours = req.advance_warning_hours or 48
        advance_notice_days = req.advance_notice_days if req.advance_notice_days is not None else max(1, round(advance_warning_hours / 24.0))

    plan = MaintenancePlan(
        plan_code=req.plan_code,
        plan_name=req.plan_name,
        plan_type=req.plan_type,
        trigger_mode=trigger_mode,
        interval_days=interval_days,
        interval_hours=interval_hours,
        advance_notice_days=advance_notice_days,
        advance_warning_hours=advance_warning_hours,
        version_no="V1.0",
        sop_content=req.sop_content,
        equipment_ids=req.equipment_ids or [],
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

@router.put("/plans/{plan_id}", response_model=BaseResponse)
def update_plan(
    plan_id: int,
    req: MaintenancePlanCreateRequest,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id, MaintenancePlan.is_deleted == False).first()
    if not plan:
        raise BusinessException(code=40001, message="维护计划不存在", status_code=404)

    # 版本号自增: V1.0 -> V1.1
    current_version = plan.version_no or "V1.0"
    if current_version.startswith("V"):
        parts = current_version[1:].split(".")
        major = int(parts[0]) if len(parts) > 0 else 1
        minor = int(parts[1]) if len(parts) > 1 else 0
        new_version = f"V{major}.{minor + 1}"
    else:
        new_version = "V1.1"

    interval_hours = req.interval_hours or (req.interval_days * 24 if req.interval_days else 720)
    interval_days = max(1, interval_hours // 24)

    plan.plan_code = req.plan_code
    plan.plan_name = req.plan_name
    plan.plan_type = req.plan_type
    plan.trigger_mode = req.trigger_mode or "CALENDAR"
    plan.interval_days = interval_days
    plan.interval_hours = interval_hours
    plan.advance_warning_hours = req.advance_warning_hours or 48
    plan.version_no = new_version
    plan.sop_content = req.sop_content
    plan.equipment_ids = req.equipment_ids or []
    plan.updated_by = current_user.id

    # 删除旧清单项，重新写入
    db.query(MaintenancePlanItem).filter(MaintenancePlanItem.plan_id == plan.id).delete()
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
    return BaseResponse(data={"plan_id": plan.id, "version_no": new_version}, message=f"维护计划已更新，版本号升至 {new_version}")

@router.get("/my-tasks", response_model=BaseResponse)
def get_my_tasks(
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    query = db.query(MaintenanceTask).filter(MaintenanceTask.status.in_(["PENDING", "IN_PROGRESS", "OVERDUE"]))
    if current_user.role_code == "TECHNICIAN":
        query = query.filter((MaintenanceTask.assigned_tech_id == current_user.id) | (MaintenanceTask.assigned_tech_id == None))

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
            "is_overdue": t.is_overdue,
            "assigned_tech_id": t.assigned_tech_id,
            "claimed_at": t.claimed_at.isoformat() if t.claimed_at else None,
            "work_order_notes": t.work_order_notes or "",
            "completion_proof_file_ids": t.completion_proof_file_ids or []
        })
    return BaseResponse(data=results)

@router.put("/tasks/{task_id}/claim", response_model=BaseResponse)
def claim_task(
    task_id: int,
    current_user: User = Depends(require_role("TECHNICIAN", "ENGINEER", "ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if not task:
        raise BusinessException(code=40001, message="目标维护工单不存在", status_code=404)
    if task.status == "COMPLETED":
        raise BusinessException(code=20001, message="该工单已完工，不可重复接单")

    task.assigned_tech_id = current_user.id
    task.status = "IN_PROGRESS"
    task.claimed_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    return BaseResponse(message="工单接单成功，已变更为执行中")

@router.put("/tasks/{task_id}/edit", response_model=BaseResponse)
def edit_task(
    task_id: int,
    req: TaskEditRequest,
    current_user: User = Depends(require_role("TECHNICIAN", "ENGINEER", "ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if not task:
        raise BusinessException(code=40001, message="目标维护工单不存在", status_code=404)

    if req.work_order_notes is not None:
        task.work_order_notes = req.work_order_notes
    if req.completion_proof_file_ids is not None:
        task.completion_proof_file_ids = req.completion_proof_file_ids

    db.commit()
    return BaseResponse(message="工单执行记录与完成证据更新成功")

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

@router.get("/completion-rate", response_model=BaseResponse[List[CompletionRateItem]])
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

@router.get("/export/maintenance-tasks", response_class=StreamingResponse)
def export_maintenance_tasks(
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    tasks = db.query(MaintenanceTask).order_by(MaintenanceTask.due_date).all()
    headers = ["工单编码", "设备编码", "设备名称", "计划日期", "截止日期", "状态", "是否超时", "技术员ID", "作业说明"]
    rows = []
    for t in tasks:
        eq = db.query(Equipment).filter(Equipment.id == t.equipment_id).first()
        rows.append([
            t.task_code,
            eq.equipment_code if eq else "",
            eq.equipment_name if eq else "",
            str(t.scheduled_date),
            str(t.due_date),
            t.status,
            "是" if t.is_overdue else "否",
            str(t.assigned_tech_id or ""),
            t.work_order_notes or ""
        ])
    excel_data = ExcelProcessor.export_to_excel(headers, rows, sheet_name="维护工单明细")
    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=maintenance_tasks.xlsx"}
    )