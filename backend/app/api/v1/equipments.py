from fastapi import APIRouter, Depends, Response, UploadFile, File
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

router = APIRouter(prefix="/equipments", tags=["设备信息管理"])

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
    # 专业数据隔离过滤 (已全局取消工种隔离，统一全量协同)
    query = apply_work_type_scope(query, Equipment, current_user)

    if equipment_type:
        query = query.filter(Equipment.equipment_type == equipment_type)
    if status:
        query = query.filter(Equipment.status == status)

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    # 批量加载位置路径信息，用于前端展示设备所属层级
    loc_ids = list(set(eq.location_id for eq in items))
    loc_map = {}
    if loc_ids:
        locs = db.query(Location).filter(Location.id.in_(loc_ids), Location.is_deleted == False).all()
        loc_map = {l.id: l for l in locs}

    resp_items = []
    for eq in items:
        resp = EquipmentResponse.model_validate(eq)
        # 加载专有参数
        param = db.query(EquipmentParam).filter(EquipmentParam.equipment_id == eq.id).first()
        if param:
            resp.params = param.extra_params
        # 附加位置路径信息
        loc = loc_map.get(eq.location_id)
        if loc:
            resp.location_path = loc.tree_path
            resp.location_name_display = loc.location_name
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

    # 挂载位置节点校验：设备只能挂载在第3级系统节点(SYSTEM)上
    loc = db.query(Location).filter(Location.id == req.location_id, Location.is_deleted == False).first()
    if not loc:
        raise BusinessException(code=20001, message="指定的位置节点不存在")
    if loc.level_depth != 3:
        raise BusinessException(code=20001, message="设备信息只能挂载在第3级系统节点(SYSTEM)上，请先选择正确的系统节点！")
    if loc.node_type != "SYSTEM":
        raise BusinessException(code=20001, message="设备信息只能挂载在系统节点(SYSTEM)上，当前节点类型为【{}】！".format(loc.node_type))

    interval_hours = req.maintenance_interval_hours or (req.maintenance_interval_days * 24 if req.maintenance_interval_days else 720)
    interval_days = max(1, interval_hours // 24)

    eq = Equipment(
        equipment_code=req.equipment_code,
        equipment_name=req.equipment_name,
        equipment_type=req.equipment_type,
        work_type=req.work_type or "GENERAL",
        location_id=req.location_id,
        manufacturer=req.manufacturer,
        model_spec=req.model_spec,
        serial_number=req.serial_number,
        purchase_date=req.purchase_date,
        commission_date=req.commission_date,
        warranty_expiry_date=req.warranty_expiry_date,
        maintenance_interval_days=interval_days,
        maintenance_interval_hours=interval_hours,
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
    return BaseResponse(data=resp, message="设备信息创建成功")

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

@router.get("/export/template")
def download_import_template(
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status)
):
    template_data = ExcelProcessor.generate_equipment_template()
    return Response(
        content=template_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=equipment_import_template.xlsx"}
    )

@router.post("/import/excel", response_model=BaseResponse)
async def import_equipments_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    contents = await file.read()
    if file.content_type and "spreadsheet" not in file.content_type and "excel" not in file.content_type:
        raise BusinessException(code=50001, message="仅支持上传 .xlsx Excel 文件")
    rows = ExcelProcessor.parse_excel(contents)
    created_count = 0
    errors = []
    for idx, row in enumerate(rows):
        row_num = idx + 2
        try:
            equipment_code = str(row.get("设备编码*", "")).strip()
            equipment_name = str(row.get("设备名称*", "")).strip()
            equipment_type = str(row.get("设备类型*", "")).strip()
            work_type = str(row.get("工种*", "")).strip()
            location_code = str(row.get("位置编码*", "")).strip()
            model_spec = str(row.get("规格型号*", "")).strip()
            interval_days_str = str(row.get("保养周期(天)", "30")).strip()
            if not all([equipment_code, equipment_name, equipment_type, work_type, location_code, model_spec]):
                errors.append(f"第{row_num}行: 必填字段缺失")
                continue
            location = db.query(Location).filter(Location.location_code == location_code, Location.is_deleted == False).first()
            if not location:
                errors.append(f"第{row_num}行: 位置编码【{location_code}】不存在")
                continue
            exist = db.query(Equipment).filter(Equipment.equipment_code == equipment_code, Equipment.is_deleted == False).first()
            if exist:
                errors.append(f"第{row_num}行: 设备编码【{equipment_code}】已存在")
                continue
            try:
                interval_days = int(interval_days_str) if interval_days_str else 30
            except ValueError:
                interval_days = 30
            eq = Equipment(
                equipment_code=equipment_code,
                equipment_name=equipment_name,
                equipment_type=equipment_type,
                work_type=work_type,
                location_id=location.id,
                model_spec=model_spec,
                maintenance_interval_days=interval_days,
                status="RUNNING",
                created_by=current_user.id
            )
            db.add(eq)
            created_count += 1
        except Exception as e:
            errors.append(f"第{row_num}行: {str(e)}")
    db.commit()
    return BaseResponse(data={
        "created_count": created_count,
        "total_rows": len(rows),
        "errors": errors
    }, message=f"成功导入 {created_count} 台设备" + (f"，{len(errors)} 行失败" if errors else ""))

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