import os
import datetime
from fastapi import APIRouter, Depends, Response, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.models.equipment import Equipment, EquipmentParam, Location, EquipmentFile
from app.models.maintenance import InspectionRecord
from app.models.fault import FaultRecord
from app.schemas.equipment import (
    EquipmentCreateRequest,
    EquipmentUpdateRequest,
    EquipmentResponse,
    EquipmentFileResponse,
    EquipmentTimelineItem,
    EquipmentOperatingLogCreateRequest,
    EquipmentOperatingSummary
)
from app.schemas.common import BaseResponse, PageResult
from app.repositories.base import apply_work_type_scope
from app.services.state_machine import EquipmentStateMachine
from app.services.excel_processor import ExcelProcessor
from app.services.equipment_meter import EquipmentMeterService
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

    # 批量加载创建人与最后修改人，兑现“每条记录最好能看到修改人是谁”
    user_ids = list(set(filter(None, [eq.created_by for eq in items] + [eq.updated_by for eq in items])))
    user_map = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        user_map = {u.id: (u.full_name or u.username) for u in users}

    resp_items = []
    for eq in items:
        resp = EquipmentResponse.model_validate(eq)
        resp.params_text = eq.params_text
        # 加载专有参数
        param = db.query(EquipmentParam).filter(EquipmentParam.equipment_id == eq.id).first()
        if param:
            resp.params = param.extra_params
            if not resp.params_text and isinstance(param.extra_params, dict) and "text" in param.extra_params:
                resp.params_text = param.extra_params["text"]
        # 附加位置路径信息
        loc = loc_map.get(eq.location_id)
        if loc:
            resp.location_path = loc.tree_path
            resp.location_name_display = loc.location_name
        # 附加创建人与修改人
        if eq.created_by and eq.created_by in user_map:
            resp.created_by_name = user_map[eq.created_by]
        if eq.updated_by and eq.updated_by in user_map:
            resp.updated_by_name = user_map[eq.updated_by]
        resp.updated_at = eq.updated_at
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
    commission_or_today = req.commission_date or datetime.date.today()
    next_maint = commission_or_today + datetime.timedelta(days=interval_days)

    eq = Equipment(
        equipment_code=req.equipment_code,
        equipment_name=req.equipment_name,
        equipment_type=req.equipment_type or "GENERAL",
        work_type=req.work_type or "GENERAL",
        location_id=req.location_id,
        manufacturer=req.manufacturer,
        model_spec=req.model_spec,
        serial_number=req.serial_number,
        rated_voltage=req.rated_voltage,
        params_text=req.params_text,
        purchase_date=req.purchase_date,
        commission_date=req.commission_date,
        warranty_expiry_date=req.warranty_expiry_date,
        maintenance_interval_days=interval_days,
        maintenance_interval_hours=interval_hours,
        next_maintenance_date=next_maint,
        responsible_engineer_id=req.responsible_engineer_id or current_user.id,
        status="RUNNING",
        created_by=current_user.id
    )
    db.add(eq)
    db.flush()

    if req.params_text or req.params:
        extra = {}
        if isinstance(req.params, dict):
            extra = dict(req.params)
        if req.params_text:
            extra["text"] = req.params_text
        param = EquipmentParam(
            equipment_id=eq.id,
            extra_params=extra
        )
        db.add(param)

    db.commit()
    db.refresh(eq)
    
    resp = EquipmentResponse.model_validate(eq)
    resp.params_text = eq.params_text
    resp.params = req.params or ({"text": req.params_text} if req.params_text else None)
    resp.created_by_name = current_user.full_name or current_user.username
    resp.location_path = loc.tree_path
    resp.location_name_display = loc.location_name
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

    headers = ["设备编码", "设备名称", "规格型号", "额定电压", "运行状态", "累计工时(小时)", "设备参数信息"]
    rows = []
    for eq in equipments:
        rows.append([
            eq.equipment_code,
            eq.equipment_name,
            eq.model_spec,
            eq.rated_voltage or "-",
            eq.status,
            float(eq.current_operating_hours or 0.0),
            eq.params_text or ""
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
            equipment_code = str(row.get("设备编码*", "") or row.get("设备编码", "")).strip()
            equipment_name = str(row.get("设备名称*", "") or row.get("设备名称", "")).strip()
            location_code = str(row.get("位置编码*", "") or row.get("位置编码", "")).strip()
            model_spec = str(row.get("规格型号*", "") or row.get("规格型号", "")).strip()
            rated_voltage = str(row.get("额定电压", "")).strip() or "380V"
            params_text = str(row.get("设备参数信息", "") or row.get("参数信息", "")).strip() or None
            equipment_type = str(row.get("设备类型*", "") or row.get("设备类型", "GENERAL")).strip() or "GENERAL"
            work_type = str(row.get("工种*", "") or row.get("责任专业", "GENERAL")).strip() or "GENERAL"

            if not all([equipment_code, equipment_name, location_code, model_spec]):
                errors.append(f"第{row_num}行: 必填字段缺失(设备编码/设备名称/规格型号/位置编码)")
                continue
            location = db.query(Location).filter(Location.location_code == location_code, Location.is_deleted == False).first()
            if not location:
                errors.append(f"第{row_num}行: 位置编码【{location_code}】不存在")
                continue
            exist = db.query(Equipment).filter(Equipment.equipment_code == equipment_code, Equipment.is_deleted == False).first()
            if exist:
                errors.append(f"第{row_num}行: 设备编码【{equipment_code}】已存在")
                continue

            eq = Equipment(
                equipment_code=equipment_code,
                equipment_name=equipment_name,
                equipment_type=equipment_type,
                work_type=work_type,
                location_id=location.id,
                model_spec=model_spec,
                rated_voltage=rated_voltage,
                params_text=params_text,
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

@router.put("/{eq_id}", response_model=BaseResponse[EquipmentResponse])
def update_equipment(
    eq_id: int,
    req: EquipmentUpdateRequest,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    eq = db.query(Equipment).filter(Equipment.id == eq_id, Equipment.is_deleted == False).first()
    if not eq:
        raise BusinessException(code=40001, message="设备不存在", status_code=404)

    if req.location_id is not None:
        loc = db.query(Location).filter(Location.id == req.location_id, Location.is_deleted == False).first()
        if not loc:
            raise BusinessException(code=20001, message="指定的位置节点不存在")
        if loc.level_depth != 3 or loc.node_type != "SYSTEM":
            raise BusinessException(code=20001, message="设备信息只能挂载在第3级系统节点(SYSTEM)上！")
        eq.location_id = req.location_id

    if req.equipment_name is not None:
        eq.equipment_name = req.equipment_name
    if req.manufacturer is not None:
        eq.manufacturer = req.manufacturer
    if req.model_spec is not None:
        eq.model_spec = req.model_spec
    if req.serial_number is not None:
        eq.serial_number = req.serial_number
    if req.rated_voltage is not None:
        eq.rated_voltage = req.rated_voltage
    if req.params_text is not None:
        eq.params_text = req.params_text
    if req.responsible_engineer_id is not None:
        eq.responsible_engineer_id = req.responsible_engineer_id
    if req.status is not None:
        eq.status = req.status
    if req.maintenance_interval_days is not None:
        eq.maintenance_interval_days = req.maintenance_interval_days
        eq.maintenance_interval_hours = req.maintenance_interval_days * 24
    if req.maintenance_interval_hours is not None:
        eq.maintenance_interval_hours = req.maintenance_interval_hours
        eq.maintenance_interval_days = max(1, req.maintenance_interval_hours // 24)

    eq.updated_by = current_user.id

    if req.params_text is not None or req.params is not None:
        param = db.query(EquipmentParam).filter(EquipmentParam.equipment_id == eq.id).first()
        extra = {}
        if isinstance(req.params, dict):
            extra = dict(req.params)
        if req.params_text is not None:
            extra["text"] = req.params_text
        if not param:
            param = EquipmentParam(equipment_id=eq.id, extra_params=extra)
            db.add(param)
        else:
            param.extra_params = extra

    db.commit()
    db.refresh(eq)

    resp = EquipmentResponse.model_validate(eq)
    resp.params_text = eq.params_text
    resp.params = req.params or ({"text": req.params_text} if req.params_text else None)
    resp.updated_by = current_user.id
    resp.updated_by_name = current_user.full_name or current_user.username
    resp.updated_at = eq.updated_at
    if eq.created_by:
        creator = db.query(User).filter(User.id == eq.created_by).first()
        if creator:
            resp.created_by_name = creator.full_name or creator.username
    loc = db.query(Location).filter(Location.id == eq.location_id).first()
    if loc:
        resp.location_path = loc.tree_path
        resp.location_name_display = loc.location_name

    return BaseResponse(data=resp, message="设备信息修改成功")

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

@router.get("/{eq_id}/files", response_model=BaseResponse[List[EquipmentFileResponse]])
def get_equipment_files(
    eq_id: int,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """获取设备关联的附件列表（照片、说明书PDF、电气图纸Word/CAD等）"""
    files = db.query(EquipmentFile).filter(
        EquipmentFile.equipment_id == eq_id,
        EquipmentFile.is_linked == True
    ).order_by(EquipmentFile.created_at.desc()).all()

    user_ids = list(set(filter(None, [f.created_by for f in files])))
    user_map = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        user_map = {u.id: (u.full_name or u.username) for u in users}

    results = []
    for f in files:
        results.append(EquipmentFileResponse(
            id=f.id,
            equipment_id=f.equipment_id,
            file_tag=f.file_tag,
            original_filename=f.original_filename,
            file_size_bytes=f.file_size_bytes,
            mime_type=f.mime_type,
            url=f"/uploads/{os.path.basename(f.storage_path)}",
            created_at=f.created_at,
            created_by_name=user_map.get(f.created_by, "系统")
        ))
    return BaseResponse(data=results)

@router.post("/{eq_id}/files/bind", response_model=BaseResponse)
def bind_equipment_file(
    eq_id: int,
    payload: dict,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """将已上传的文件与设备进行业务关联绑定"""
    file_id = payload.get("file_id")
    file_tag = payload.get("file_tag", "PHOTO")
    if not file_id:
        raise BusinessException(code=40001, message="缺少 file_id 参数")
    file_rec = db.query(EquipmentFile).filter(EquipmentFile.id == file_id).first()
    if not file_rec:
        raise BusinessException(code=40001, message="附件不存在", status_code=404)
    file_rec.equipment_id = eq_id
    file_rec.file_tag = file_tag
    file_rec.is_linked = True
    db.commit()
    return BaseResponse(message="附件与设备绑定成功")

@router.delete("/{eq_id}/files/{file_id}", response_model=BaseResponse)
def delete_equipment_file(
    eq_id: int,
    file_id: int,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """解绑或删除设备附件"""
    file_rec = db.query(EquipmentFile).filter(EquipmentFile.id == file_id, EquipmentFile.equipment_id == eq_id).first()
    if not file_rec:
        raise BusinessException(code=40001, message="附件不存在或不属于该设备", status_code=404)
    file_rec.is_linked = False
    file_rec.equipment_id = None
    db.commit()
    return BaseResponse(message="附件已移除")

# =========================================================================
# 设备每日运行工时填报与预测性维保引擎 API (SWR-MNT-012)
# =========================================================================

@router.post("/{eq_id}/operating-hours", response_model=BaseResponse)
def record_equipment_operating_hours(
    eq_id: int,
    req: EquipmentOperatingLogCreateRequest,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """
    现场操作员/技术员每日填报机台实际运行工时 (SWR-MNT-012):
    - 校验单日累计工时不得超过 24.0 小时
    - 原子递增累计工时并落库流水
    - 达到提前预警阈值 (如 720h - 48h = 672h) 时触发防重邮件与工单派发
    """
    req.equipment_id = eq_id
    result = EquipmentMeterService.record_operating_hours(db, current_user, req)
    return BaseResponse(data=result, message=result.get("message", "工时填报成功"))

@router.get("/{eq_id}/operating-summary", response_model=BaseResponse[EquipmentOperatingSummary])
def get_equipment_operating_summary(
    eq_id: int,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """查询单台设备当前维保周期的累计工时、进度比例、预警状态"""
    summary = EquipmentMeterService.get_operating_summary(db, eq_id)
    return BaseResponse(data=summary)

@router.get("/{eq_id}/operating-logs", response_model=BaseResponse[List[dict]])
def get_equipment_operating_logs(
    eq_id: int,
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """查询设备的每日运行工时填报历史流水"""
    logs = EquipmentMeterService.get_operating_logs(db, eq_id, limit)
    return BaseResponse(data=logs)

@router.get("/operating-overview/all", response_model=BaseResponse[List[EquipmentOperatingSummary]])
def get_all_operating_overview(
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """批量查询所有活跃设备的工时进度汇总列表（供现场工时打卡及监控展示）"""
    equipments = db.query(Equipment).filter(Equipment.is_deleted == False).order_by(Equipment.id).all()
    summaries = []
    for eq in equipments:
        try:
            summaries.append(EquipmentMeterService.get_operating_summary(db, eq.id))
        except Exception:
            continue
    return BaseResponse(data=summaries)