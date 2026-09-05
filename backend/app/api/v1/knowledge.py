from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.models.knowledge import KnowledgeArticle
from app.schemas.common import BaseResponse, PageResult
from app.api.deps import get_current_user, require_role, check_fcp_status
from app.core.exceptions import BusinessException

router = APIRouter(prefix="/knowledge", tags=["维修知识库"])

@router.get("/search", response_model=BaseResponse)
def search_knowledge(
    keyword: Optional[str] = None,
    equipment_type: Optional[str] = None,
    fault_system: Optional[str] = None,
    is_featured: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    query = db.query(KnowledgeArticle).filter(KnowledgeArticle.is_deleted == False)

    if equipment_type:
        query = query.filter(KnowledgeArticle.equipment_type == equipment_type)
    if fault_system:
        query = query.filter(KnowledgeArticle.fault_system == fault_system)
    if is_featured is not None:
        query = query.filter(KnowledgeArticle.is_featured == is_featured)
    if keyword:
        term = f"%{keyword}%"
        query = query.filter(
            (KnowledgeArticle.fault_title.ilike(term)) |
            (KnowledgeArticle.fault_phenomenon.ilike(term)) |
            (KnowledgeArticle.root_cause.ilike(term)) |
            (KnowledgeArticle.solution_steps.ilike(term)) |
            (KnowledgeArticle.equipment_model.ilike(term))
        )

    total = query.count()
    items = query.order_by(KnowledgeArticle.is_featured.desc(), KnowledgeArticle.created_at.desc()).offset(skip).limit(limit).all()

    return BaseResponse(data=PageResult(
        items=[{
            "id": a.id,
            "article_code": a.article_code,
            "equipment_type": a.equipment_type,
            "equipment_model": a.equipment_model,
            "fault_system": a.fault_system,
            "fault_title": a.fault_title,
            "fault_phenomenon": a.fault_phenomenon,
            "root_cause": a.root_cause,
            "solution_steps": a.solution_steps,
            "tags": a.tags,
            "is_featured": a.is_featured,
            "view_count": a.view_count,
            "created_at": str(a.created_at)
        } for a in items],
        total=total,
        page=(skip // limit) + 1,
        page_size=limit
    ))

@router.put("/{article_id}/feature", response_model=BaseResponse)
def toggle_feature_article(
    article_id: int,
    is_featured: bool,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    article = db.query(KnowledgeArticle).filter(KnowledgeArticle.id == article_id, KnowledgeArticle.is_deleted == False).first()
    if not article:
        raise BusinessException(code=40001, message="知识库条目不存在", status_code=404)
    article.is_featured = is_featured
    db.commit()
    return BaseResponse(message=f"典型案例标记已{'启用' if is_featured else '取消'}")
