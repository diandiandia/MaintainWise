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
    if req.role_code not in ["ADMIN", "ENGINEER", "TECHNICIAN"]:
        raise BusinessException(code=20003, message="系统不支持该角色或车间主管已下线，仅支持 ADMIN/ENGINEER/TECHNICIAN")

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
        work_type=req.work_type or "GENERAL",
        is_active=True,
        force_change_password=True,
        created_by=current_user.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return BaseResponse(data=UserResponse.model_validate(user), message="用户创建成功")

@router.put("/{user_id}", response_model=BaseResponse)
def update_user(
    user_id: int,
    req: UserUpdateRequest,
    current_user: User = Depends(require_role("ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    if req.role_code and req.role_code not in ["ADMIN", "ENGINEER", "TECHNICIAN"]:
        raise BusinessException(code=20003, message="系统不支持该角色或车间主管已下线，仅支持 ADMIN/ENGINEER/TECHNICIAN")
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise BusinessException(code=40001, message="目标用户不存在", status_code=404)
    if req.is_active is not None:
        if user.id == current_user.id and not req.is_active:
            raise BusinessException(code=10003, message="管理员不能禁用自身账户", status_code=400)
        user.is_active = req.is_active
    if req.full_name is not None:
        user.full_name = req.full_name
    if req.email is not None:
        user.email = req.email
    if req.phone is not None:
        user.phone = req.phone
    if req.role_code is not None:
        user.role_code = req.role_code
    if req.work_type is not None:
        user.work_type = req.work_type
    db.commit()
    return BaseResponse(data=UserResponse.model_validate(user), message="用户信息已更新")

@router.delete("/{user_id}", response_model=BaseResponse)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_role("ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise BusinessException(code=40001, message="目标用户不存在", status_code=404)
    if user.id == current_user.id:
        raise BusinessException(code=10003, message="管理员不能删除自身账户", status_code=400)
    user.is_deleted = True
    db.commit()
    return BaseResponse(message="用户已成功软删除")
