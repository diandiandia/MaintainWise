from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, BigInteger, Text, ForeignKey, JSON
from app.models.base import BaseAuditModel, utc_now

class KnowledgeArticle(BaseAuditModel):
    __tablename__ = "knowledge_articles"

    article_code = Column(String(64), unique=True, nullable=False, index=True)
    source_fault_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("fault_records.id", ondelete="SET NULL"), nullable=True)
    equipment_type = Column(String(32), nullable=False, index=True)
    equipment_model = Column(String(128), nullable=False, index=True)
    fault_system = Column(String(64), nullable=False, index=True)
    fault_title = Column(String(128), nullable=False)
    fault_phenomenon = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=False)
    solution_steps = Column(Text, nullable=False)
    tags = Column(JSON, default=list, nullable=False) # e.g. ["#轴承磨损", "#异响"]
    is_featured = Column(Boolean, default=False, nullable=False, index=True)
    view_count = Column(Integer, default=0, nullable=False)
    helpful_count = Column(Integer, default=0, nullable=False)
