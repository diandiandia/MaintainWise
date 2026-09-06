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

@router.get("/records", response_model=BaseResponse)
def list_training_records(
    current_user: User = Depends(get_current_user),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """查询设备检修培训记录清单 (SWR-TRN-003)"""
    records = db.query(TrainingRecord).order_by(TrainingRecord.training_date.desc()).all()
    results = []
    for r in records:
        course = db.query(TrainingCourse).filter(TrainingCourse.id == r.course_id).first()
        scores = db.query(TrainingUserScore).filter(TrainingUserScore.training_record_id == r.id).all()
        passed = sum(1 for s in scores if s.is_passed)
        results.append({
            "id": r.id,
            "course_id": r.course_id,
            "course_name": course.course_name if course else "未指定课程",
            "training_date": str(r.training_date),
            "instructor_name": r.instructor_name,
            "location": r.location,
            "trainees_count": len(scores),
            "pass_count": passed,
            "pass_rate": round(passed / len(scores) * 100, 1) if scores else 100.0,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    return BaseResponse(data=results)

@router.post("/records", response_model=BaseResponse)
def create_training_record(
    payload: dict,
    current_user: User = Depends(require_role("ADMIN", "ENGINEER")),
    _fcp: User = Depends(check_fcp_status),
    db: Session = Depends(get_db)
):
    """登记一次设备检修培训记录与打分成绩 (SWR-TRN-003/004)"""
    import datetime
    training_date = payload.get("training_date")
    if isinstance(training_date, str):
        try:
            training_date = datetime.date.fromisoformat(training_date)
        except ValueError:
            training_date = datetime.date.today()
    elif not training_date:
        training_date = datetime.date.today()

    record = TrainingRecord(
        course_id=payload["course_id"],
        training_date=training_date,
        instructor_name=payload.get("instructor_name", current_user.full_name or "主讲工程师"),
        location=payload.get("location", "车间实训区"),
        live_photo_id=payload.get("live_photo_id"),
        created_by=current_user.id
    )
    db.add(record)
    db.flush()

    trainees = payload.get("trainees", [])
    for t in trainees:
        user_id = t["user_id"]
        score = float(t.get("score", 85))
        is_passed = score >= 60.0
        score_entry = TrainingUserScore(
            training_record_id=record.id,
            user_id=user_id,
            assessment_type=t.get("assessment_type", "PRACTICAL"),
            score=score,
            is_passed=is_passed,
            need_retraining=not is_passed,
            retraining_completed=False
        )
        db.add(score_entry)

    db.commit()
    return BaseResponse(data={"record_id": record.id}, message="检修培训记录登记成功")
