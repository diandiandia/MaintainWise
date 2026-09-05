from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreateRequest, UserUpdateRequest, UserResponse
from app.schemas.common import BaseResponse, PageResult
from app.core.exceptions import BusinessException
from app.api.deps import require_role, check_fcp_status

router = APIRouter(prefix="/users", tags=["用户管理"])

@router.get("", response_model=BaseResponse[PageResult[UserResponse]])
def list_users(
    skip: int = 0,
    limit: int = 20,
    role_code: Optional[str] = None,
    current_user: User = Depends(require_role("ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    query = db.query(User).filter(User.is_deleted == False)
    if role_code:
        query = query.filter(User.role_code == role_code)
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return BaseResponse(data=PageResult(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit
    ))

@router.post("", response_model=BaseResponse[UserResponse])
def create_user(
    req: UserCreateRequest,
    current_user: User = Depends(require_role("ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    exist = db.query(User).filter(
        (User.username == req.username) | (User.employee_no == req.employee_no),
        User.is_deleted == False
    ).first()
    if exist:
        raise BusinessException(code=20002, message="用户名或工号已存在")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        employee_no=req.employee_no,
        email=req.email,
        phone=req.phone,
        role_code=req.role_code,
        work_type=req.work_type,
        is_active=True,
        force_change_password=True,
        created_by=current_user.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return BaseResponse(data=UserResponse.model_validate(user), message="用户创建成功")

@router.put("/{user_id}/status", response_model=BaseResponse)
def toggle_user_status(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(require_role("ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise BusinessException(code=40001, message="目标用户不存在", status_code=404)
    if user.id == current_user.id:
        raise BusinessException(code=10003, message="管理员不能禁用自身账户", status_code=400)
    user.is_active = is_active
    db.commit()
    status_text = "启用" if is_active else "禁用"
    return BaseResponse(message=f"用户已成功{status_text}")
