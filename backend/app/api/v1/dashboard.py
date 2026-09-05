from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.equipment import Equipment
from app.models.maintenance import MaintenanceTask
from app.models.fault import FaultRecord
from app.schemas.common import BaseResponse
from app.api.deps import get_current_user, check_fcp_status
from app.repositories.base import apply_work_type_scope

router = APIRouter(prefix="/dashboard", tags=["数据平台"])

@router.get("/metrics", response_model=BaseResponse)
def get_metrics(
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    query = db.query(Equipment).filter(Equipment.is_deleted == False)
    query = apply_work_type_scope(query, Equipment, current_user)
    
    total = query.count()
    running = query.filter(Equipment.status == "RUNNING").count()
    pending = query.filter(Equipment.status == "MAINTENANCE_PENDING").count()
    faulty = query.filter(Equipment.status == "FAULTY").count()
    shutdown = query.filter(Equipment.status == "SHUTDOWN").count()
    
    # 待办统计
    todo_tasks = db.query(MaintenanceTask).filter(MaintenanceTask.status.in_(["PENDING", "OVERDUE"])).count()
    open_faults = db.query(FaultRecord).filter(FaultRecord.status.in_(["OPEN", "IN_PROGRESS"])).count()

    return BaseResponse(data={
        "total_equipments": total,
        "running_count": running,
        "pending_maintenance_count": pending,
        "faulty_count": faulty,
        "shutdown_count": shutdown,
        "todo_maintenance_count": todo_tasks,
        "open_faults_count": open_faults
    })

@router.get("/my-todo", response_model=BaseResponse)
def get_my_todo(
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    items = []
    if current_user.role_code == "TECHNICIAN":
        # 技术员优先展示：待执行巡检任务
        tasks = db.query(MaintenanceTask).filter(
            MaintenanceTask.assigned_tech_id == current_user.id,
            MaintenanceTask.status.in_(["PENDING", "OVERDUE"])
        ).limit(10).all()
        for t in tasks:
            items.append({
                "type": "INSPECTION",
                "title": f"维护任务: {t.task_code}",
                "due_date": str(t.due_date),
                "is_overdue": t.is_overdue,
                "priority": "HIGH" if t.is_overdue else "NORMAL"
            })
    else:
        # 工程师/管理员优先展示：待处理故障与超时报警
        faults = db.query(FaultRecord).filter(
            FaultRecord.status.in_(["OPEN", "IN_PROGRESS"])
        ).order_by(FaultRecord.reported_at.desc()).limit(10).all()
        for f in faults:
            items.append({
                "type": "FAULT",
                "title": f"故障待办: {f.fault_title}",
                "due_date": str(f.reported_at),
                "is_overdue": f.is_sla_response_breached or f.is_sla_resolve_breached,
                "priority": "CRITICAL" if f.severity_level == "CRITICAL" else "NORMAL"
            })

    return BaseResponse(data=items)
