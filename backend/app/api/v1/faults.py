import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import io
from app.core.database import get_db
from app.models.user import User
from app.models.fault import FaultRecord
from app.models.equipment import Equipment
from app.models.knowledge import KnowledgeArticle
from app.schemas.fault import FaultCreateRequest, FaultResolveRequest, FaultResponse, SimilarCaseItem
from app.schemas.common import BaseResponse, PageResult
from app.services.fault_claim import FaultClaimService
from app.services.recommend_engine import RecommendationEngine
from app.services.state_machine import FaultStateMachine, EquipmentStateMachine
from app.services.excel_processor import ExcelProcessor
from app.api.deps import get_current_user, require_role, check_fcp_status
from app.core.exceptions import BusinessException

router = APIRouter(prefix="/faults", tags=["故障流转与SLA"])

@router.post("", response_model=BaseResponse[FaultResponse])
def report_fault(
    req: FaultCreateRequest,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    eq = db.query(Equipment).filter(Equipment.id == req.equipment_id, Equipment.is_deleted == False).first()
    if not eq:
        raise BusinessException(code=20005, message="关联设备不存在")

    fault = FaultRecord(
        fault_code=f"FLT-{eq.equipment_code}-{int(datetime.datetime.utcnow().timestamp())}",
        source_type="MANUAL_REPORT",
        equipment_id=eq.id,
        snapshot_location_id=eq.location_id,
        fault_title=req.fault_title,
        fault_desc=req.fault_desc,
        fault_system=req.fault_system,
        fault_part=req.fault_part,
        severity_level=req.severity_level,
        status="OPEN",
        reported_by=current_user.id
    )
    db.add(fault)

    # 设备状态跃迁为 FAULTY
    eq.status = EquipmentStateMachine.transition(eq.status, "FAULTY")

    db.commit()
    db.refresh(fault)
    return BaseResponse(data=FaultResponse.model_validate(fault), message="故障上报成功，已分发至待处理池")

@router.post("/recommend-similar", response_model=BaseResponse[List[SimilarCaseItem]])
def recommend_similar(
    equipment_type: str,
    model_spec: str,
    fault_desc: str,
    fault_part: str = "",
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    cases = RecommendationEngine.get_similar_cases(db, equipment_type, model_spec, fault_desc, fault_part)
    return BaseResponse(data=[SimilarCaseItem(**c) for c in cases])

@router.get("", response_model=BaseResponse[PageResult[FaultResponse]])
def list_faults(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    severity_level: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    query = db.query(FaultRecord).filter(FaultRecord.is_deleted == False)
    if status:
        query = query.filter(FaultRecord.status == status)
    if severity_level:
        query = query.filter(FaultRecord.severity_level == severity_level)

    total = query.count()
    items = query.order_by(FaultRecord.reported_at.desc()).offset(skip).limit(limit).all()
    return BaseResponse(data=PageResult(
        items=[FaultResponse.model_validate(f) for f in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit
    ))

@router.put("/{fault_id}/claim", response_model=BaseResponse)
def claim_fault(
    fault_id: int,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    # 调用乐观并发锁接单服务
    res = FaultClaimService.claim_fault(db, fault_id, current_user.id)
    return BaseResponse(data=res, message="成功认领故障工单！")

@router.post("/{fault_id}/resolve", response_model=BaseResponse)
def resolve_fault(
    fault_id: int,
    req: FaultResolveRequest,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id, FaultRecord.is_deleted == False).first()
    if not fault:
        raise BusinessException(code=40001, message="故障工单不存在", status_code=404)

    fault.status = FaultStateMachine.transition(fault.status, "RESOLVED")
    fault.root_cause = req.root_cause
    fault.solution_steps = req.solution_steps
    fault.downtime_minutes = req.downtime_minutes or 0
    fault.is_featured_case = req.is_featured_case or False
    fault.resolved_at = datetime.datetime.utcnow()

    # 自动沉淀至知识库 (REQ-KB-001 / SWR-KB-001)
    eq = db.query(Equipment).filter(Equipment.id == fault.equipment_id).first()
    article = KnowledgeArticle(
        article_code=f"KB-{fault.fault_code}",
        source_fault_id=fault.id,
        equipment_type=eq.equipment_type if eq else "OTHER",
        equipment_model=eq.model_spec if eq else "UNKNOWN",
        fault_system=fault.fault_system,
        fault_title=fault.fault_title,
        fault_phenomenon=fault.fault_desc,
        root_cause=fault.root_cause,
        solution_steps=fault.solution_steps,
        tags=[f"#{fault.fault_system}", f"#{fault.fault_part}"],
        is_featured=fault.is_featured_case,
        created_by=current_user.id
    )
    db.add(article)

    # 恢复关联设备运行状态
    if eq and eq.status == "FAULTY":
        eq.status = "RUNNING"

    db.commit()
    return BaseResponse(message="故障维修结果已提交，自动归档并沉淀为知识条目！")

@router.put("/{fault_id}/close", response_model=BaseResponse)
def close_fault(
    fault_id: int,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id, FaultRecord.is_deleted == False).first()
    if not fault:
        raise BusinessException(code=40001, message="故障工单不存在", status_code=404)
    fault.status = FaultStateMachine.transition(fault.status, "CLOSED")
    fault.closed_at = datetime.datetime.utcnow()
    db.commit()
    return BaseResponse(message="工单已正式验收归档关闭")

@router.get("/export/faults", response_class=StreamingResponse)
def export_faults(
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    faults = db.query(FaultRecord).filter(FaultRecord.is_deleted == False).order_by(FaultRecord.reported_at.desc()).all()
    headers = ["故障编码", "故障标题", "故障描述", "故障系统", "故障部件", "严重级别", "状态", "上报时间", "根因分析", "解决步骤", "停机时间(分钟)", "是否精选案例"]
    rows = []
    for f in faults:
        rows.append([
            f.fault_code,
            f.fault_title,
            f.fault_desc,
            f.fault_system,
            f.fault_part,
            f.severity_level,
            f.status,
            str(f.reported_at),
            f.root_cause or "",
            f.solution_steps or "",
            f.downtime_minutes,
            "是" if f.is_featured_case else "否"
        ])
    excel_data = ExcelProcessor.export_to_excel(headers, rows, sheet_name="故障明细")
    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=fault_records.xlsx"}
    )