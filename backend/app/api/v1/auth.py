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
