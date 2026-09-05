import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.fault import FaultRecord
from app.models.user import User
from app.core.exceptions import BusinessException

class FaultClaimService:
    @staticmethod
    def claim_fault(db: Session, fault_id: int, engineer_id: int) -> dict:
        """
        故障接单原子条件乐观更新:
        仅当状态处于 OPEN 时允许认领并更新为 IN_PROGRESS
        """
        stmt = text("""
            UPDATE fault_records
            SET status = 'IN_PROGRESS',
                assigned_engineer_id = :engineer_id,
                claimed_at = :now,
                updated_at = :now
            WHERE id = :fault_id AND status = 'OPEN' AND is_deleted = false
        """)
        now = datetime.datetime.now(datetime.timezone.utc)
        result = db.execute(stmt, {"engineer_id": engineer_id, "fault_id": fault_id, "now": now})
        db.commit()

        if result.rowcount == 0:
            # 查询是谁抢先认领了
            fault = db.query(FaultRecord).filter(FaultRecord.id == fault_id).first()
            if not fault:
                raise BusinessException(code=40001, message="故障工单不存在或已被删除", status_code=404)
            if fault.status != "OPEN":
                engineer_name = "其他工程师"
                if fault.assigned_engineer_id:
                    eng = db.query(User).filter(User.id == fault.assigned_engineer_id).first()
                    if eng:
                        engineer_name = eng.full_name
                raise BusinessException(
                    code=40003,
                    message=f"接单冲突：该工单已被【{engineer_name}】抢先认领！",
                    status_code=409
                )

        return {"fault_id": fault_id, "status": "IN_PROGRESS"}
