import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.equipment import Equipment, EquipmentOperatingLog
from app.models.maintenance import MaintenancePlan, MaintenanceTask, MaintenanceNotifyLog
from app.models.user import User
from app.schemas.equipment import EquipmentOperatingLogCreateRequest
from app.core.exceptions import BusinessException
import logging

logger = logging.getLogger(__name__)

class EquipmentMeterService:
    @staticmethod
    def record_operating_hours(
        db: Session,
        current_user: User,
        req: EquipmentOperatingLogCreateRequest
    ) -> Dict[str, Any]:
        """
        录入设备每日运行工时并执行动态维保阈值判定 (SWR-MNT-012):
        1. 强校验设备有效性
        2. 强校验当日单日累计工时不得超过 24.0 小时
        3. 原子累加设备当前运行工时 current_operating_hours
        4. 写入流水日志表 equipment_operating_logs
        5. 检查维护计划阈值 (如 720h) 与提前预警阈值 (如 48h)
        6. 满足预警条件时触发防重邮件提醒与待办维护工单派发
        """
        equipment = db.query(Equipment).filter(
            Equipment.id == req.equipment_id,
            Equipment.is_deleted == False
        ).first()

        if not equipment:
            raise BusinessException(code=20005, message="目标设备不存在或已被删除")

        if req.duration_hours <= 0:
            raise BusinessException(code=20007, message="填报运行工时必须大于 0 小时")
        if req.duration_hours > 24.0:
            raise BusinessException(code=20007, message="单次填报运行工时不得超过 24 小时")

        log_date = req.log_date or datetime.date.today()

        # 校验当日单台设备累计工时 <= 24.0h
        logged_today_sum = db.query(func.sum(EquipmentOperatingLog.duration_hours)).filter(
            EquipmentOperatingLog.equipment_id == equipment.id,
            EquipmentOperatingLog.log_date == log_date
        ).scalar() or Decimal('0.0')

        if float(logged_today_sum) + req.duration_hours > 24.0001:
            raise BusinessException(
                code=20007,
                message=f"单日累计运行工时不能超过 24 小时（设备【{equipment.equipment_name}】在 {log_date} 已填报 {float(logged_today_sum):.1f} 小时，本次填报 {req.duration_hours:.1f} 小时已超出限制）"
            )

        # 原子累加
        new_hours = float(equipment.current_operating_hours or 0) + req.duration_hours
        equipment.current_operating_hours = new_hours

        # 写入流水记录
        log_entry = EquipmentOperatingLog(
            equipment_id=equipment.id,
            log_date=log_date,
            duration_hours=req.duration_hours,
            cumulative_hours=new_hours,
            proof_image_id=req.proof_image_id,
            operator_id=current_user.id,
            remarks=req.remarks
        )
        db.add(log_entry)
        db.flush()

        # 查找适用的维护计划
        matching_plans = db.query(MaintenancePlan).filter(
            MaintenancePlan.is_active == True,
            MaintenancePlan.is_deleted == False
        ).all()

        applicable_plan = None
        for p in matching_plans:
            eq_ids = p.equipment_ids or []
            if equipment.id in eq_ids:
                applicable_plan = p
                break

        if not applicable_plan and matching_plans:
            applicable_plan = matching_plans[0]

        interval_hours = (applicable_plan.interval_hours if applicable_plan and applicable_plan.interval_hours else (equipment.maintenance_interval_hours or 720))
        advance_warning_hours = (applicable_plan.advance_warning_hours if applicable_plan and applicable_plan.advance_warning_hours else 48)

        remaining_hours = max(0.0, float(interval_hours) - new_hours)
        is_warning = remaining_hours <= float(advance_warning_hours)
        is_due = new_hours >= float(interval_hours)

        warning_triggered = False
        task_created = False

        plan_id = applicable_plan.id if applicable_plan else 1
        plan_version = applicable_plan.version_no if applicable_plan else "V1.0"

        # 触发提前预警通知与自动调度工单
        today_date = datetime.date.today()
        if is_warning:
            notify_stage = int(interval_hours)
            exist_log = db.query(MaintenanceNotifyLog).filter(
                MaintenanceNotifyLog.equipment_id == equipment.id,
                MaintenanceNotifyLog.target_notify_date == today_date,
                MaintenanceNotifyLog.notify_stage == notify_stage
            ).first()

            if not exist_log:
                warning_triggered = True
                notify_log = MaintenanceNotifyLog(
                    equipment_id=equipment.id,
                    task_id=None,
                    target_notify_date=today_date,
                    notify_stage=notify_stage,
                    recipient_email=current_user.email or "maintenance-team@maintainwise.com",
                    status="SUCCESS"
                )
                db.add(notify_log)
                logger.info(
                    f"【工时预警邮件通知】设备 [{equipment.equipment_code}] {equipment.equipment_name} "
                    f"已累计运行 {new_hours:.1f} 小时，距 {interval_hours} 小时阈值还剩 {remaining_hours:.1f} 小时！"
                )

            # 自动生成待办工单 (如果当前尚无进行中的任务)
            today_date = datetime.date.today()
            exist_task = db.query(MaintenanceTask).filter(
                MaintenanceTask.equipment_id == equipment.id,
                MaintenanceTask.status.in_(["PENDING", "IN_PROGRESS"])
            ).first()

            if not exist_task:
                task = MaintenanceTask(
                    task_code=f"TSK-METER-{equipment.equipment_code}-{today_date.strftime('%Y%m%d')}",
                    plan_id=plan_id,
                    equipment_id=equipment.id,
                    assigned_tech_id=equipment.responsible_engineer_id or current_user.id,
                    plan_version_snapshot=plan_version,
                    scheduled_date=today_date,
                    due_date=today_date + datetime.timedelta(days=3),
                    status="PENDING"
                )
                db.add(task)
                task_created = True

        # 若达到维保周期，设备状态跃迁
        if is_due and equipment.status == "RUNNING":
            equipment.status = "MAINTENANCE_PENDING"

        db.commit()

        progress_pct = min(100.0, round((new_hours / float(interval_hours)) * 100, 1))

        return {
            "log_id": log_entry.id,
            "equipment_id": equipment.id,
            "equipment_name": equipment.equipment_name,
            "duration_hours": req.duration_hours,
            "cumulative_hours": new_hours,
            "current_operating_hours": new_hours,
            "interval_hours": interval_hours,
            "advance_warning_hours": advance_warning_hours,
            "remaining_hours": remaining_hours,
            "progress_percentage": progress_pct,
            "is_warning": is_warning,
            "is_due": is_due,
            "warning_triggered": warning_triggered,
            "task_created": task_created,
            "triggered_maintenance": is_warning or task_created,
            "message": (
                f"工时填报成功！当前累计 {new_hours:.1f}/{interval_hours} 小时 ({progress_pct}%)"
                + ("【已触发提前维护预警及派单】" if is_warning else "")
            )
        }

    @staticmethod
    def get_operating_summary(db: Session, equipment_id: int) -> Dict[str, Any]:
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.is_deleted == False
        ).first()

        if not equipment:
            raise BusinessException(code=20005, message="设备不存在")

        matching_plans = db.query(MaintenancePlan).filter(
            MaintenancePlan.is_active == True,
            MaintenancePlan.is_deleted == False
        ).all()

        applicable_plan = None
        for p in matching_plans:
            eq_ids = p.equipment_ids or []
            if equipment.id in eq_ids:
                applicable_plan = p
                break

        interval_hours = (applicable_plan.interval_hours if applicable_plan and applicable_plan.interval_hours else (equipment.maintenance_interval_hours or 720))
        advance_warning_hours = (applicable_plan.advance_warning_hours if applicable_plan and applicable_plan.advance_warning_hours else 48)

        current_hours = float(equipment.current_operating_hours or 0.0)
        remaining_hours = max(0.0, float(interval_hours) - current_hours)
        progress_pct = min(100.0, round((current_hours / float(interval_hours)) * 100, 1)) if interval_hours > 0 else 0.0

        last_log = db.query(EquipmentOperatingLog).filter(
            EquipmentOperatingLog.equipment_id == equipment.id
        ).order_by(EquipmentOperatingLog.log_date.desc()).first()

        return {
            "equipment_id": equipment.id,
            "equipment_code": equipment.equipment_code,
            "equipment_name": equipment.equipment_name,
            "current_operating_hours": current_hours,
            "interval_hours": interval_hours,
            "advance_warning_hours": advance_warning_hours,
            "remaining_hours": remaining_hours,
            "progress_percentage": progress_pct,
            "is_warning": remaining_hours <= float(advance_warning_hours),
            "is_due": current_hours >= float(interval_hours),
            "status": equipment.status,
            "last_log_date": str(last_log.log_date) if last_log else None
        }

    @staticmethod
    def get_operating_logs(db: Session, equipment_id: int, limit: int = 30) -> List[Dict[str, Any]]:
        logs = db.query(EquipmentOperatingLog).filter(
            EquipmentOperatingLog.equipment_id == equipment_id
        ).order_by(EquipmentOperatingLog.created_at.desc()).limit(limit).all()

        results = []
        for l in logs:
            op_user = db.query(User).filter(User.id == l.operator_id).first()
            results.append({
                "id": l.id,
                "equipment_id": l.equipment_id,
                "log_date": str(l.log_date),
                "duration_hours": float(l.duration_hours),
                "cumulative_hours": float(l.cumulative_hours),
                "proof_image_id": l.proof_image_id,
                "operator_id": l.operator_id,
                "operator_name": op_user.full_name if op_user else "系统",
                "remarks": l.remarks,
                "created_at": l.created_at.isoformat() if l.created_at else None
            })
        return results

    @staticmethod
    def reset_operating_hours(db: Session, equipment_id: int):
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if equipment:
            equipment.current_operating_hours = 0.0
            db.query(MaintenanceNotifyLog).filter(
                MaintenanceNotifyLog.notify_type.like(f"OPERATING_HOURS_WARN_{equipment_id}_%")
            ).delete(synchronize_session=False)
            db.commit()
