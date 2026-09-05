from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.user import User
from app.models.equipment import Location, Equipment
from app.schemas.equipment import LocationCreateRequest, LocationResponse
from app.schemas.common import BaseResponse
from app.core.exceptions import BusinessException
from app.api.deps import get_current_user, require_role, check_fcp_status

router = APIRouter(prefix="/locations", tags=["位置层级树"])

@router.get("/tree", response_model=BaseResponse[List[LocationResponse]])
def get_location_tree(
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    locs = db.query(Location).filter(Location.is_deleted == False).order_by(Location.sort_order).all()
    # 构造树形结构
    node_map = {l.id: LocationResponse.model_validate(l) for l in locs}
    tree = []
    for l in locs:
        node = node_map[l.id]
        if l.parent_id and l.parent_id in node_map:
            node_map[l.parent_id].children.append(node)
        else:
            tree.append(node)
    return BaseResponse(data=tree)

@router.post("", response_model=BaseResponse[LocationResponse])
def create_location(
    req: LocationCreateRequest,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    parent = None
    level_depth = 1
    tree_path = ""
    if req.parent_id:
        parent = db.query(Location).filter(Location.id == req.parent_id, Location.is_deleted == False).first()
        if not parent:
            raise BusinessException(code=20001, message="指定的父节点不存在")
        if parent.level_depth >= 5:
            raise BusinessException(code=20004, message="位置层级超出限制，系统最高仅支持5级")
        level_depth = parent.level_depth + 1
        tree_path = parent.tree_path
        # 父节点之前如果是叶子节点，更新为非叶子节点
        parent.is_leaf = False

    loc = Location(
        parent_id=req.parent_id,
        location_name=req.location_name,
        location_code=req.location_code,
        level_depth=level_depth,
        tree_path="", # 稍后回填
        is_leaf=True,
        sort_order=req.sort_order or 0,
        created_by=current_user.id
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)

    loc.tree_path = f"{tree_path}{loc.id}/" if tree_path else f"/{loc.id}/"
    db.commit()
    db.refresh(loc)

    return BaseResponse(data=LocationResponse.model_validate(loc), message="位置节点创建成功")

@router.delete("/{loc_id}", response_model=BaseResponse)
def delete_location(
    loc_id: int,
    current_user: User = Depends(require_role("ADMIN")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    loc = db.query(Location).filter(Location.id == loc_id, Location.is_deleted == False).first()
    if not loc:
        raise BusinessException(code=40001, message="目标位置节点不存在", status_code=404)
    
    # 防孤儿校验：是否存在未删除子节点
    has_children = db.query(Location).filter(Location.parent_id == loc_id, Location.is_deleted == False).first()
    if has_children:
        raise BusinessException(code=20001, message="该位置节点下存在子节点，禁止直接删除！")

    # 防孤儿校验：是否存在下挂设备
    has_equipment = db.query(Equipment).filter(Equipment.location_id == loc_id, Equipment.is_deleted == False).first()
    if has_equipment:
        raise BusinessException(code=20001, message="该位置节点下存在挂载设备，禁止直接删除！")

    loc.is_deleted = True
    db.commit()
    return BaseResponse(message="位置节点删除成功")
