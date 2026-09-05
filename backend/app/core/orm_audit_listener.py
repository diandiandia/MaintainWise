from sqlalchemy import event
from sqlalchemy.orm import Session
from app.core.audit_context import current_user_id

def setup_orm_audit_listeners():
    from app.core.database import Base

    @event.listens_for(Session, "before_flush")
    def auto_inject_audit_fields(session: Session, flush_context, instances):
        for obj in session.new:
            if hasattr(obj, "created_by") and current_user_id.get(None) is not None:
                obj.created_by = current_user_id.get()
        for obj in session.dirty:
            if hasattr(obj, "updated_by") and current_user_id.get(None) is not None:
                obj.updated_by = current_user_id.get()