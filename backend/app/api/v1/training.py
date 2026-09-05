from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.models.training import TrainingCourse, TrainingCourseCase, TrainingRecord, TrainingUserScore
from app.schemas.common import BaseResponse
from app.api.deps import get_current_user, require_role, check_fcp_status
from app.core.exceptions import BusinessException

router = APIRouter(prefix="/training", tags=["培训实操与技能档案"])

@router.get("/courses", response_model=BaseResponse)
def list_courses(
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    courses = db.query(TrainingCourse).filter(TrainingCourse.is_deleted == False).all()
    results = []
    for c in courses:
        cases = db.query(TrainingCourseCase).filter(TrainingCourseCase.course_id == c.id).count()
        results.append({
            "id": c.id,
            "course_code": c.course_code,
            "course_name": c.course_name,
            "course_category": c.course_category,
            "planned_hours": float(c.planned_hours),
            "description": c.description,
            "cases_count": cases
        })
    return BaseResponse(data=results)

@router.post("/courses", response_model=BaseResponse)
def create_course(
    payload: dict,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    course = TrainingCourse(
        course_code=payload["course_code"],
        course_name=payload["course_name"],
        course_category=payload["course_category"],
        planned_hours=payload["planned_hours"],
        description=payload.get("description"),
        created_by=current_user.id
    )
    db.add(course)
    db.flush()

    # 挂接知识库典型案例 (REQ-TRN-002)
    case_ids = payload.get("case_article_ids", [])
    for aid in case_ids:
        db.add(TrainingCourseCase(course_id=course.id, article_id=aid))

    db.commit()
    return BaseResponse(data={"course_id": course.id}, message="培训课程与实操案例挂接成功")

@router.get("/profile/{user_id}", response_model=BaseResponse)
def get_user_training_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(code=40001, message="用户不存在", status_code=404)

    scores = db.query(TrainingUserScore).filter(TrainingUserScore.user_id == user_id).all()
    total_trainings = len(scores)
    passed_count = sum(1 for s in scores if s.is_passed)
    pass_rate = round(passed_count / total_trainings * 100, 1) if total_trainings > 0 else 0.0
    need_retrain = any(s.need_retraining and not s.retraining_completed for s in scores)

    return BaseResponse(data={
        "user_id": user.id,
        "full_name": user.full_name,
        "employee_no": user.employee_no,
        "role_code": user.role_code,
        "work_type": user.work_type,
        "total_trainings": total_trainings,
        "pass_rate": pass_rate,
        "need_retraining": need_retrain,
        "history": [{
            "score_id": s.id,
            "assessment_type": s.assessment_type,
            "score": float(s.score),
            "is_passed": s.is_passed,
            "need_retraining": s.need_retraining,
            "date": str(s.created_at)
        } for s in scores]
    })
