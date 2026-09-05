from app.core.exceptions import BusinessException

class EquipmentStateMachine:
    VALID_TRANSITIONS = {
        "RUNNING": {"MAINTENANCE_PENDING", "FAULTY", "SHUTDOWN", "SCRAPPED"},
        "MAINTENANCE_PENDING": {"RUNNING", "FAULTY", "SCRAPPED"},
        "FAULTY": {"RUNNING", "SCRAPPED"},
        "SHUTDOWN": {"RUNNING", "SCRAPPED"},
        "SCRAPPED": set(), # 终态不可逆
    }

    @classmethod
    def transition(cls, current_status: str, target_status: str) -> str:
        if current_status == target_status:
            return target_status
        allowed = cls.VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise BusinessException(
                code=20005,
                message=f"设备状态不允许从【{current_status}】跃迁到【{target_status}】"
            )
        return target_status

class FaultStateMachine:
    VALID_TRANSITIONS = {
        "OPEN": {"IN_PROGRESS"},
        "IN_PROGRESS": {"RESOLVED_PENDING_REVIEW", "RESOLVED"},
        "RESOLVED_PENDING_REVIEW": {"RESOLVED", "IN_PROGRESS"},
        "RESOLVED": {"CLOSED", "IN_PROGRESS", "OPEN"},
        "CLOSED": {"IN_PROGRESS", "OPEN"},
        "REOPENED": {"IN_PROGRESS"},
    }

    @classmethod
    def transition(cls, current_status: str, target_status: str) -> str:
        if current_status == target_status:
            return target_status
        allowed = cls.VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise BusinessException(
                code=40002,
                message=f"故障单状态不允许从【{current_status}】流转到【{target_status}】"
            )
        return target_status
