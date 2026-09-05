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
    include_equipments: bool = False,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    locs = db.query(Location).filter(Location.is_deleted == False).order_by(Location.sort_order).all()
    # 构造树形结构
    node_map = {}
    for l in locs:
        # node_type 推断：优先使用数据库中的值，若为默认值 "SYSTEM" 则根据 level_depth 推断
        db_node_type = getattr(l, "node_type", None)
        if db_node_type and db_node_type != "SYSTEM":
            inferred_type = db_node_type
        else:
            inferred_type = "FACTORY" if l.level_depth == 1 else ("DEPARTMENT" if l.level_depth == 2 else "SYSTEM")
        resp = LocationResponse(
            id=l.id,
            parent_id=l.parent_id,
            location_name=l.location_name,
            location_code=l.location_code,
            level_depth=l.level_depth,
            node_type=inferred_type,
            tree_path=l.tree_path,
            is_leaf=l.is_leaf,
            sort_order=l.sort_order,
            children=[]
        )
        node_map[l.id] = resp

    tree = []
    for l in locs:
        node = node_map[l.id]
        if l.parent_id and l.parent_id in node_map:
            node_map[l.parent_id].children.append(node)
        else:
            tree.append(node)

    # 若请求包含第 4 级设备信息，将设备作为叶子节点挂在所属系统/工位节点下
    if include_equipments:
        eqs = db.query(Equipment).filter(Equipment.is_deleted == False).all()
        for eq in eqs:
            if eq.location_id in node_map:
                eq_node = LocationResponse(
                    id=f"eq_{eq.id}",
                    parent_id=eq.location_id,
                    location_name=f"{eq.equipment_name} ({eq.equipment_code})",
                    location_code=eq.equipment_code,
                    level_depth=4,
                    node_type="EQUIPMENT",
                    tree_path=f"{node_map[eq.location_id].tree_path}eq_{eq.id}/",
                    is_leaf=True,
                    sort_order=0,
                    equipment_id=eq.id,
                    children=[]
                )
                node_map[eq.location_id].children.append(eq_node)

    return BaseResponse(data=tree)

@router.post("", response_model=BaseResponse[LocationResponse])
def create_location(
    req: LocationCreateRequest,
    current_user: User = Depends(require_role("ADMIN")), # 管理员录入工厂、部门、系统
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    parent = None
    level_depth = 1
    tree_path = ""
    node_type = "FACTORY"

    if req.parent_id:
        parent = db.query(Location).filter(Location.id == req.parent_id, Location.is_deleted == False).first()
        if not parent:
            raise BusinessException(code=20001, message="指定的父节点不存在")
        if parent.level_depth >= 3:
            raise BusinessException(code=20004, message="车间层级最高支持3级位置(工厂->部门->系统)，第4级为设备信息")
        level_depth = parent.level_depth + 1
        tree_path = parent.tree_path
        # 父节点之前如果是叶子节点，更新为非叶子节点
        parent.is_leaf = False
        if level_depth == 2:
            node_type = "DEPARTMENT"
        elif level_depth == 3:
            node_type = "SYSTEM"
    else:
        level_depth = 1
        node_type = "FACTORY"

    # 若指定了 node_type 则使用，否则按层级自动确定 (1: FACTORY, 2: DEPARTMENT, 3: SYSTEM)
    final_node_type = req.node_type or node_type

    # 校验编码唯一性
    exist_code = db.query(Location).filter(Location.location_code == req.location_code, Location.is_deleted == False).first()
    if exist_code:
        raise BusinessException(code=20002, message=f"位置编码【{req.location_code}】已存在")

    loc = Location(
        parent_id=req.parent_id,
        location_name=req.location_name,
        location_code=req.location_code,
        level_depth=level_depth,
        node_type=final_node_type,
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

    res_data = LocationResponse(
        id=loc.id,
        parent_id=loc.parent_id,
        location_name=loc.location_name,
        location_code=loc.location_code,
        level_depth=loc.level_depth,
        node_type=loc.node_type,
        tree_path=loc.tree_path,
        is_leaf=loc.is_leaf,
        sort_order=loc.sort_order,
        children=[]
    )
    return BaseResponse(data=res_data, message="位置节点创建成功")

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