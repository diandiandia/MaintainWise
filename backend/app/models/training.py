from datetime import datetime, date
from sqlalchemy import Column, String, Boolean, DateTime, Date, Integer, BigInteger, Numeric, Text, ForeignKey, UniqueConstraint
from app.core.database import Base
from app.models.base import BaseAuditModel, utc_now

class TrainingCourse(BaseAuditModel):
    __tablename__ = "training_courses"

    course_code = Column(String(64), unique=True, nullable=False, index=True)
    course_name = Column(String(128), nullable=False)
    course_category = Column(String(64), nullable=False, index=True) # ONBOARDING, SPECIAL_EQUIP, ANNUAL_SAFETY, FAULT_CASE_STUDY
    planned_hours = Column(Numeric(4, 1), nullable=False)
    description = Column(Text, nullable=True)
    material_file_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipment_files.id"), nullable=True)

class TrainingCourseCase(Base):
    __tablename__ = "training_course_cases"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    course_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("training_courses.id", ondelete="CASCADE"), nullable=False, index=True)
    article_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("knowledge_articles.id", ondelete="CASCADE"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("course_id", "article_id", name="uq_course_case"),
    )

class TrainingRecord(Base):
    __tablename__ = "training_records"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    course_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("training_courses.id"), nullable=False, index=True)
    training_date = Column(Date, nullable=False, index=True)
    instructor_name = Column(String(64), nullable=False)
    location = Column(String(128), nullable=False)
    live_photo_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("equipment_files.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    created_by = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("sys_users.id"), nullable=True)

class TrainingUserScore(Base):
    __tablename__ = "training_user_scores"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    training_record_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("training_records.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("sys_users.id"), nullable=False, index=True)
    assessment_type = Column(String(32), nullable=False) # WRITTEN, PRACTICAL, ORAL
    score = Column(Numeric(5, 2), nullable=False)
    is_passed = Column(Boolean, nullable=False, index=True)
    need_retraining = Column(Boolean, default=False, nullable=False, index=True)
    retraining_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
