from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.models.equipment import Equipment, EquipmentParam, Location
from app.models.maintenance import InspectionRecord
from app.models.fault import FaultRecord
from app.schemas.equipment import EquipmentCreateRequest, EquipmentUpdateRequest, EquipmentResponse, EquipmentTimelineItem
from app.schemas.common import BaseResponse, PageResult
from app.repositories.base import apply_work_type_scope
from app.services.state_machine import EquipmentStateMachine
from app.services.excel_processor import ExcelProcessor
from app.core.exceptions import BusinessException
from app.api.deps import get_current_user, require_role, check_fcp_status

router = APIRouter(prefix="/equipments", tags=["设备台账管理"])

@router.get("", response_model=BaseResponse[PageResult[EquipmentResponse]])
def list_equipments(
    skip: int = 0,
    limit: int = 20,
    equipment_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    query = db.query(Equipment).filter(Equipment.is_deleted == False)
    # 专业数据隔离过滤
    query = apply_work_type_scope(query, Equipment, current_user)

    if equipment_type:
        query = query.filter(Equipment.equipment_type == equipment_type)
    if status:
        query = query.filter(Equipment.status == status)

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    resp_items = []
    for eq in items:
        resp = EquipmentResponse.model_validate(eq)
        # 加载专有参数
        param = db.query(EquipmentParam).filter(EquipmentParam.equipment_id == eq.id).first()
        if param:
            resp.params = param.extra_params
        resp_items.append(resp)

    return BaseResponse(data=PageResult(
        items=resp_items,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit
    ))

@router.post("", response_model=BaseResponse[EquipmentResponse])
def create_equipment(
    req: EquipmentCreateRequest,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    # 编码唯一性检查
    exist = db.query(Equipment).filter(Equipment.equipment_code == req.equipment_code, Equipment.is_deleted == False).first()
    if exist:
        raise BusinessException(code=20002, message=f"设备编码【{req.equipment_code}】已存在")

    # 挂载位置节点校验：只能挂载在叶子节点上
    loc = db.query(Location).filter(Location.id == req.location_id, Location.is_deleted == False).first()
    if not loc:
        raise BusinessException(code=20001, message="指定的位置节点不存在")
    if not loc.is_leaf:
        raise BusinessException(code=20001, message="设备只能挂载在最底层工位叶子节点上！")

    eq = Equipment(
        equipment_code=req.equipment_code,
        equipment_name=req.equipment_name,
        equipment_type=req.equipment_type,
        work_type=req.work_type,
        location_id=req.location_id,
        manufacturer=req.manufacturer,
        model_spec=req.model_spec,
        serial_number=req.serial_number,
        purchase_date=req.purchase_date,
        commission_date=req.commission_date,
        warranty_expiry_date=req.warranty_expiry_date,
        maintenance_interval_days=req.maintenance_interval_days or 30,
        responsible_engineer_id=req.responsible_engineer_id or current_user.id,
        status="RUNNING",
        created_by=current_user.id
    )
    db.add(eq)
    db.flush()

    if req.params:
        param = EquipmentParam(
            equipment_id=eq.id,
            extra_params=req.params
        )
        db.add(param)

    db.commit()
    db.refresh(eq)
    
    resp = EquipmentResponse.model_validate(eq)
    resp.params = req.params
    return BaseResponse(data=resp, message="设备台账创建成功")

@router.get("/{eq_id}/timeline", response_model=BaseResponse[List[EquipmentTimelineItem]])
def get_equipment_timeline(
    eq_id: int,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    timeline = []
    # 巡检事件
    inspections = db.query(InspectionRecord).filter(InspectionRecord.equipment_id == eq_id).all()
    for insp in inspections:
        timeline.append(EquipmentTimelineItem(
            timestamp=insp.created_at,
            event_type="INSPECTION",
            title="日常巡检打卡",
            description=f"巡检判定结果: {'异常发现' if insp.has_anomaly else '设备正常'}",
            operator_name="技术员"
        ))

    # 故障事件
    faults = db.query(FaultRecord).filter(FaultRecord.equipment_id == eq_id).all()
    for flt in faults:
        timeline.append(EquipmentTimelineItem(
            timestamp=flt.reported_at,
            event_type="FAULT",
            title=f"故障事件: {flt.fault_title}",
            description=f"原因: {flt.root_cause or '排查中'} | 方案: {flt.solution_steps or '待修复'}",
            downtime_minutes=flt.downtime_minutes
        ))

    timeline.sort(key=lambda x: x.timestamp, reverse=True)
    return BaseResponse(data=timeline)

@router.get("/export/excel")
def export_equipments_excel(
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    query = db.query(Equipment).filter(Equipment.is_deleted == False)
    query = apply_work_type_scope(query, Equipment, current_user)
    equipments = query.all()

    headers = ["设备编码", "设备名称", "设备类型", "专业类型", "规格型号", "运行状态", "维护周期(天)"]
    rows = []
    for eq in equipments:
        rows.append([
            eq.equipment_code,
            eq.equipment_name,
            eq.equipment_type,
            eq.work_type,
            eq.model_spec,
            eq.status,
            eq.maintenance_interval_days
        ])

    excel_data = ExcelProcessor.export_to_excel(headers, rows, sheet_name="设备台账")
    return Response(
        content=excel_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=equipments.xlsx"}
    )

@router.delete("/{eq_id}", response_model=BaseResponse)
def delete_equipment(
    eq_id: int,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    eq = db.query(Equipment).filter(Equipment.id == eq_id, Equipment.is_deleted == False).first()
    if not eq:
        raise BusinessException(code=40001, message="设备不存在", status_code=404)
    eq.is_deleted = True
    db.commit()
    return BaseResponse(message="设备已安全软删除")
