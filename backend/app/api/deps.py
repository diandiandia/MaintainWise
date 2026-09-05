from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.core.exceptions import BusinessException

def get_current_user(
    authorization: str = Header(..., description="Bearer JWT Token"),
    db: Session = Depends(get_db)
) -> User:
    if not authorization.startswith("Bearer "):
        raise BusinessException(code=10004, message="认证头格式错误，必须为 Bearer Token", status_code=401)
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BusinessException(code=10004, message="无效的凭证", status_code=401)
        
    user = db.query(User).filter(User.id == int(user_id), User.is_deleted == False).first()
    if not user:
        raise BusinessException(code=10004, message="用户不存在", status_code=401)
    if not user.is_active:
        raise BusinessException(code=10002, message="账户已被管理员禁用", status_code=403)
        
    return user

def require_role(*allowed_roles: str):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role_code not in allowed_roles:
            raise BusinessException(
                code=10003,
                message=f"权限不足：当前角色【{current_user.role_code}】无权访问此功能",
                status_code=403
            )
        return current_user
    return role_checker

def check_fcp_status(current_user: User = Depends(get_current_user)) -> User:
    """强制改密校验 (SWR-USR-004)"""
    if current_user.force_change_password:
        raise BusinessException(
            code=10008,
            message="首次登录或密码过期，必须修改初始密码后方可继续操作",
            status_code=403
        )
    return current_user
