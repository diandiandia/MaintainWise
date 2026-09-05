import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.fault import FaultRecord
import logging

logger = logging.getLogger(__name__)

SLA_RESPONSE_LIMITS_MINUTES = {
    "CRITICAL": 30,
    "MAJOR": 120,
    "MINOR": 480
}

SLA_RESOLVE_LIMITS_HOURS = {
    "CRITICAL": 4,
    "MAJOR": 24,
    "MINOR": 72
}

def run_sla_monitor_job(db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    now = datetime.datetime.now(datetime.timezone.utc)
    breached_count = 0

    try:
        faults = db.query(FaultRecord).filter(
            FaultRecord.status.in_(["OPEN", "IN_PROGRESS"]),
            FaultRecord.is_deleted == False
        ).all()

        for f in faults:
            reported_time = f.reported_at
            if reported_time.tzinfo is None:
                reported_time = reported_time.replace(tzinfo=datetime.timezone.utc)

            # 1. 响应时效检查
            if f.status == "OPEN":
                diff_minutes = (now - reported_time).total_seconds() / 60
                limit = SLA_RESPONSE_LIMITS_MINUTES.get(f.severity_level, 120)
                if diff_minutes > limit and not f.is_sla_response_breached:
                    f.is_sla_response_breached = True
                    breached_count += 1

            # 2. 解决时效检查
            diff_hours = (now - reported_time).total_seconds() / 3600
            resolve_limit = SLA_RESOLVE_LIMITS_HOURS.get(f.severity_level, 24)
            if diff_hours > resolve_limit and not f.is_sla_resolve_breached:
                f.is_sla_resolve_breached = True
                breached_count += 1

        db.commit()
        return {"breached_faults": breached_count}
    finally:
        if close_db:
            db.close()
