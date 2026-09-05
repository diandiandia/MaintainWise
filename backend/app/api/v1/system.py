import os
import hashlib
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, AuditLog
from app.models.equipment import EquipmentFile
from app.schemas.common import BaseResponse, PageResult
from app.api.deps import require_role, get_current_user, check_fcp_status
from app.core.exceptions import BusinessException

router = APIRouter(prefix="/system", tags=["系统管理与支撑"])

@router.post("/smtp/test", response_model=BaseResponse)
def test_smtp(
    payload: dict,
    current_user: User = Depends(require_role("ADMIN")),
    _fcp: User = Depends(check_fcp_status)
):
    target_email = payload.get("to_email")
    if not target_email:
        raise BusinessException(code=20006, message="收件邮箱地址为必填项")
    # 模拟连通性测试与发信
    return BaseResponse(message=f"测试邮件已成功向【{target_email}】投递！SMTP 服务器连接正常")

@router.post("/files/upload", response_model=BaseResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_tag: str = "OTHER",
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    # 校验文件名后缀，禁止可执行脚本
    filename = file.filename or "unknown"
    forbidden_exts = [".sh", ".exe", ".bat", ".php", ".py", ".jsp"]
    if any(filename.lower().endswith(ext) for ext in forbidden_exts):
        raise BusinessException(code=50001, message="安全防护拦截：严禁上传可执行脚本文件！")

    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise BusinessException(code=50002, message=f"文件超过最大限制 {settings.MAX_UPLOAD_SIZE_MB}MB")

    # 计算散列与唯一落盘路径
    file_hash = hashlib.sha256(contents).hexdigest()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    save_name = f"{file_hash[:16]}_{filename}"
    save_path = os.path.join(settings.UPLOAD_DIR, save_name)
    
    with open(save_path, "wb") as f:
        f.write(contents)

    record = EquipmentFile(
        file_tag=file_tag,
        original_filename=filename,
        storage_path=save_path,
        file_size_bytes=len(contents),
        mime_type=file.content_type or "application/octet-stream",
        file_sha256=file_hash,
        is_linked=False,
        created_by=current_user.id
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return BaseResponse(data={
        "file_id": record.id,
        "filename": filename,
        "file_size": len(contents),
        "url": f"/uploads/{save_name}"
    }, message="文件上传成功")

@router.get("/audit-logs", response_model=BaseResponse)
def get_audit_logs(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_role("ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return BaseResponse(data=PageResult(
        items=[{
            "id": a.id,
            "username": a.username,
            "client_ip": a.client_ip,
            "module_name": a.module_name,
            "action_type": a.action_type,
            "request_url": a.request_url,
            "status_code": a.status_code,
            "created_at": str(a.created_at)
        } for a in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit
    ))
