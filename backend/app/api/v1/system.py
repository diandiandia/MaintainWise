import os
import hashlib
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, AuditLog
from app.models.equipment import EquipmentFile
from app.models.system import SystemSmtpConfig
from app.schemas.common import BaseResponse, PageResult
from app.schemas.system import SmtpConfigSaveRequest, SmtpConfigResponse, SmtpTestRequest
from app.services.email_service import EmailService
from app.api.deps import require_role, get_current_user, check_fcp_status
from app.core.exceptions import BusinessException

MAGIC_NUMBERS = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/zip",
}

def validate_file_magic(contents: bytes, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    ext_to_expected = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".zip": "application/zip",
    }
    if ext not in ext_to_expected:
        return contents[:4].hex()[:8]
    expected_mime = ext_to_expected[ext]
    for magic, mime_type in MAGIC_NUMBERS.items():
        if contents.startswith(magic) and mime_type == expected_mime:
            return mime_type
    raise BusinessException(
        code=50003,
        message=f"文件安全校验失败：上传文件后缀为 {ext}，但实际文件类型不匹配，禁止上传伪造后缀文件"
    )

router = APIRouter(prefix="/system", tags=["系统管理与支撑"])

@router.get("/smtp/config", response_model=BaseResponse)
def get_smtp_config(
    current_user: User = Depends(require_role("ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """获取当前生效的 SMTP 邮件服务器配置 (密码脱敏)"""
    config = db.query(SystemSmtpConfig).order_by(SystemSmtpConfig.id.desc()).first()
    if not config:
        config = SystemSmtpConfig(
            smtp_host="smtp.maintainwise.com",
            smtp_port=465,
            smtp_user="noreply@maintainwise.com",
            smtp_pass="InitialSmtpAuth2026",
            sender_name="MaintainWise 智能运维中心",
            use_ssl=True,
            use_tls=False,
            is_active=True
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    resp_data = SmtpConfigResponse(
        id=config.id,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_pass_masked="******" if config.smtp_pass else "",
        sender_name=config.sender_name,
        use_ssl=config.use_ssl,
        use_tls=config.use_tls,
        is_active=config.is_active,
        updated_at=config.updated_at,
        updated_by=config.updated_by
    )
    return BaseResponse(data=resp_data.model_dump())

@router.post("/smtp/config", response_model=BaseResponse)
def save_smtp_config(
    payload: SmtpConfigSaveRequest,
    current_user: User = Depends(require_role("ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """页面配置并保存 SMTP 邮件服务器参数 (支持动态热更新)"""
    config = db.query(SystemSmtpConfig).order_by(SystemSmtpConfig.id.desc()).first()
    if not config:
        config = SystemSmtpConfig(
            smtp_host=payload.smtp_host,
            smtp_port=payload.smtp_port,
            smtp_user=payload.smtp_user,
            smtp_pass=payload.smtp_pass or "DefaultPass2026",
            sender_name=payload.sender_name,
            use_ssl=payload.use_ssl,
            use_tls=payload.use_tls,
            is_active=payload.is_active,
            updated_by=current_user.id
        )
        db.add(config)
    else:
        config.smtp_host = payload.smtp_host
        config.smtp_port = payload.smtp_port
        config.smtp_user = payload.smtp_user
        if payload.smtp_pass and payload.smtp_pass.strip() and payload.smtp_pass != "******":
            config.smtp_pass = payload.smtp_pass.strip()
        config.sender_name = payload.sender_name
        config.use_ssl = payload.use_ssl
        config.use_tls = payload.use_tls
        config.is_active = payload.is_active
        config.updated_by = current_user.id

    # 审计日志注入
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        client_ip="127.0.0.1",
        module_name="SYSTEM_SMTP",
        action_type="UPDATE",
        request_url="/api/v1/system/smtp/config",
        request_method="POST",
        diff_payload={"smtp_host": config.smtp_host, "smtp_user": config.smtp_user, "is_active": config.is_active},
        status_code=200
    )
    db.add(audit)
    db.commit()
    db.refresh(config)

    resp_data = SmtpConfigResponse(
        id=config.id,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        smtp_pass_masked="******" if config.smtp_pass else "",
        sender_name=config.sender_name,
        use_ssl=config.use_ssl,
        use_tls=config.use_tls,
        is_active=config.is_active,
        updated_at=config.updated_at,
        updated_by=config.updated_by
    )
    return BaseResponse(data=resp_data.model_dump(), message="SMTP 邮件服务器配置已成功保存！")

@router.post("/smtp/test", response_model=BaseResponse)
def test_smtp(
    payload: SmtpTestRequest,
    current_user: User = Depends(require_role("ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """SMTP 连通性在线测试 (支持已保存配置或传入表单草稿即时自检)"""
    target_email = payload.to_email
    if not target_email or "@" not in target_email:
        raise BusinessException(code=20006, message="请输入合法的收件邮箱地址")

    test_config = None
    if payload.smtp_host and payload.smtp_user:
        pass_to_use = payload.smtp_pass
        if not pass_to_use or pass_to_use == "******":
            saved = db.query(SystemSmtpConfig).order_by(SystemSmtpConfig.id.desc()).first()
            pass_to_use = saved.smtp_pass if saved else ""

        test_config = SystemSmtpConfig(
            smtp_host=payload.smtp_host,
            smtp_port=payload.smtp_port or 465,
            smtp_user=payload.smtp_user,
            smtp_pass=pass_to_use or "",
            sender_name=payload.sender_name or "MaintainWise 智能运维中心",
            use_ssl=payload.use_ssl if payload.use_ssl is not None else True,
            use_tls=payload.use_tls if payload.use_tls is not None else False,
            is_active=True
        )

    result = EmailService.send_email(
        to_email=target_email,
        subject="【MaintainWise】SMTP 邮件服务器配置自检成功",
        content="尊敬的管理员：\n\n您在 MaintainWise 工厂设备维护系统控制台提交的 SMTP 邮件服务器连通性自检已成功通过！\n\n系统后续将通过此通道向运维团队派发工单到期提醒、SLA告警与巡检异常通知。",
        config=test_config,
        db=db
    )

    return BaseResponse(message=result.get("message", f"测试邮件已成功向【{target_email}】投递！SMTP 服务器连接正常"))

@router.post("/upload", response_model=BaseResponse)
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

    # 魔数校验：禁止伪造后缀文件上传
    validated_mime = validate_file_magic(contents, filename)

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