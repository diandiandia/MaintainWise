from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy.orm import Session
from app.models.base import BaseAuditModel
from app.models.user import User

ModelType = TypeVar("ModelType", bound=BaseAuditModel)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id, self.model.is_deleted == False).first()

    def list(self, db: Session, skip: int = 0, limit: int = 20) -> List[ModelType]:
        return db.query(self.model).filter(self.model.is_deleted == False).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ModelType, creator_id: Optional[int] = None) -> ModelType:
        if hasattr(obj_in, "created_by") and creator_id:
            obj_in.created_by = creator_id
        db.add(obj_in)
        db.commit()
        db.refresh(obj_in)
        return obj_in

    def soft_delete(self, db: Session, id: Any, operator_id: Optional[int] = None) -> bool:
        item = self.get(db, id)
        if not item:
            return False
        item.is_deleted = True
        if hasattr(item, "updated_by") and operator_id:
            item.updated_by = operator_id
        db.commit()
        return True

def apply_work_type_scope(query, model, current_user: User):
    """
    根据新业务规范，取消责任工种数据隔离，支持跨专业全量协同，统一放行所有数据 (不再进行工种过滤)
    """
    return query
