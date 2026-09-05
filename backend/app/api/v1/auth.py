from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, hash_password, create_access_token
from app.models.user import User
from app.schemas.user import UserLoginRequest, ForceChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest
from app.schemas.common import BaseResponse
from app.core.exceptions import BusinessException
from app.api.deps import get_current_user
from app.core.redis import redis_client
from app.services.email_service import EmailService
import secrets

router = APIRouter(prefix="/auth", tags=["身份认证与权限"])

@router.post("/login", response_model=BaseResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username, User.is_deleted == False).first()
    
    # 检查锁定
    now = datetime.now(timezone.utc)
    if user and user.locked_until and user.locked_until.replace(tzinfo=timezone.utc) > now:
        remaining = int((user.locked_until.replace(tzinfo=timezone.utc) - now).total_seconds())
        raise BusinessException(code=10001, message=f"账号已被安全锁定，请在 {remaining} 秒后再试", status_code=403)

    if not user or not verify_password(req.password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)
                db.commit()
                raise BusinessException(code=10001, message="连续5次密码错误，账户已被安全锁定15分钟", status_code=403)
            db.commit()
        raise BusinessException(code=10005, message="用户名或密码错误", status_code=400)

    if not user.is_active:
        raise BusinessException(code=10002, message="账户已被管理员禁用", status_code=403)

    # 密码90天过期检查
    if user.password_updated_at:
        pwd_age = (now - user.password_updated_at.replace(tzinfo=timezone.utc)).days
        if pwd_age > 90:
            user.force_change_password = True
            db.commit()
            token = create_access_token({
                "sub": str(user.id),
                "username": user.username,
                "role": user.role_code,
                "work_type": user.work_type,
                "fcp": True
            })
            return BaseResponse(data={
                "access_token": token,
                "token_type": "bearer",
                "force_change_password": True
            }, message="密码已超过90天有效期，请立即修改密码")

    # 登录成功，重置失败次数
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role_code,
        "work_type": user.work_type,
        "fcp": user.force_change_password
    })

    return BaseResponse(data={
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role_code": user.role_code,
        "work_type": user.work_type,
        "force_change_password": user.force_change_password
    })

@router.post("/force-change-password", response_model=BaseResponse)
def force_change_password(
    req: ForceChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(req.old_password, current_user.password_hash):
        raise BusinessException(code=10005, message="原密码校验错误", status_code=400)
    
    current_user.password_hash = hash_password(req.new_password)
    current_user.force_change_password = False
    current_user.password_updated_at = datetime.now(timezone.utc)
    db.commit()

    return BaseResponse(message="密码修改成功，已解除首次改密限制")

@router.get("/me", response_model=BaseResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return BaseResponse(data={
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "employee_no": current_user.employee_no,
        "email": current_user.email,
        "role_code": current_user.role_code,
        "work_type": current_user.work_type,
        "force_change_password": current_user.force_change_password
    })

@router.post("/forgot-password", response_model=BaseResponse)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email, User.is_deleted == False, User.is_active == True).first()
    if not user:
        return BaseResponse(message="如果该邮箱已注册，重置密码链接已发送至您的邮箱")
    token = secrets.token_urlsafe(32)
    redis_client.setex(f"pwd_reset:{token}", 900, str(user.id))
    EmailService.send_email(
        to_email=user.email,
        subject="MaintainWise 密码重置",
        content=f"尊敬的用户 {user.full_name}：\n\n点击下方链接重置密码（有效期15分钟）：\n\n重置链接：http://localhost:3000/reset-password?token={token}\n\n若非您本人操作，请忽略此邮件。",
        is_html=False,
        db=db
    )
    return BaseResponse(message="如果该邮箱已注册，重置密码链接已发送至您的邮箱")

@router.post("/reset-password", response_model=BaseResponse)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    user_id_str = redis_client.get(f"pwd_reset:{req.token}")
    if not user_id_str:
        raise BusinessException(code=10005, message="重置链接已过期或无效，请重新申请", status_code=400)
    user = db.query(User).filter(User.id == int(user_id_str), User.is_deleted == False).first()
    if not user:
        raise BusinessException(code=10005, message="用户不存在或已被禁用", status_code=400)
    user.password_hash = hash_password(req.new_password)
    user.password_updated_at = datetime.now(timezone.utc)
    user.force_change_password = False
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    redis_client.delete(f"pwd_reset:{req.token}")
    return BaseResponse(message="密码重置成功，请使用新密码登录")