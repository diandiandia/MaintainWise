import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.equipment import Equipment
from app.models.maintenance import MaintenancePlan, MaintenanceTask
import logging

logger = logging.getLogger(__name__)

def run_daily_maintenance_countdown_job(db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    today = datetime.date.today()
    updated_count = 0
    new_tasks_count = 0

    try:
        # 获取所有启用的维护计划及其关联的设备ID列表
        plans = db.query(MaintenancePlan).filter(
            MaintenancePlan.is_active == True,
            MaintenancePlan.is_deleted == False
        ).all()

        processed_eq_ids = set()

        for plan in plans:
            equipment_ids = plan.equipment_ids or []
            if not equipment_ids:
                continue

            equipments = db.query(Equipment).filter(
                Equipment.id.in_(equipment_ids),
                Equipment.status.in_(["RUNNING", "MAINTENANCE_PENDING"]),
                Equipment.is_deleted == False
            ).all()

            for eq in equipments:
                processed_eq_ids.add(eq.id)
                try:
                    if eq.next_maintenance_date is None:
                        interval = plan.interval_days or eq.maintenance_interval_days or 30
                        eq.next_maintenance_date = today + datetime.timedelta(days=interval)
                        db.commit()

                    delta_days = (eq.next_maintenance_date - today).days

                    # 1. 倒计时到期：状态跃迁并派发工单
                    if delta_days <= 0 and eq.status == "RUNNING":
                        eq.status = "MAINTENANCE_PENDING"
                        updated_count += 1

                        # 防重复生成今日待办
                        exist_task = db.query(MaintenanceTask).filter(
                            MaintenanceTask.equipment_id == eq.id,
                            MaintenanceTask.plan_id == plan.id,
                            MaintenanceTask.scheduled_date == today,
                            MaintenanceTask.status == "PENDING"
                        ).first()

                        if not exist_task:
                            task = MaintenanceTask(
                                task_code=f"TSK-{eq.equipment_code}-{today.strftime('%Y%m%d')}",
                                plan_id=plan.id,
                                equipment_id=eq.id,
                                assigned_tech_id=eq.responsible_engineer_id,
                                plan_version_snapshot=plan.version_no,
                                scheduled_date=today,
                                due_date=today + datetime.timedelta(days=3),
                                status="PENDING"
                            )
                            db.add(task)
                            new_tasks_count += 1

                    # 2. 超时未维护判定 (超过截止日期3天)
                    tasks = db.query(MaintenanceTask).filter(
                        MaintenanceTask.equipment_id == eq.id,
                        MaintenanceTask.status == "PENDING",
                        MaintenanceTask.due_date < today
                    ).all()
                    for t in tasks:
                        t.status = "OVERDUE"
                        t.is_overdue = True

                    db.commit()
                except Exception as ex:
                    db.rollback()
                    logger.error(f"设备 ID={eq.id} 倒计时调度异常: {str(ex)}")

        # 2. 兜底扫描：未显式指定维护计划的常规设备 (兼容基础测试与未分配计划设备)
        fallback_plan = plans[0] if plans else None
        fallback_plan_id = fallback_plan.id if fallback_plan else 1
        fallback_version = fallback_plan.version_no if fallback_plan else "V1.0"

        unassigned_query = db.query(Equipment).filter(
            Equipment.status.in_(["RUNNING", "MAINTENANCE_PENDING"]),
            Equipment.is_deleted == False
        )
        if processed_eq_ids:
            unassigned_query = unassigned_query.filter(~Equipment.id.in_(processed_eq_ids))

        unassigned_equipments = unassigned_query.all()
        for eq in unassigned_equipments:
            try:
                if eq.next_maintenance_date is None:
                    interval = eq.maintenance_interval_days or 30
                    eq.next_maintenance_date = today + datetime.timedelta(days=interval)
                    db.commit()

                delta_days = (eq.next_maintenance_date - today).days
                if delta_days <= 0 and eq.status == "RUNNING":
                    eq.status = "MAINTENANCE_PENDING"
                    updated_count += 1

                    exist_task = db.query(MaintenanceTask).filter(
                        MaintenanceTask.equipment_id == eq.id,
                        MaintenanceTask.scheduled_date == today,
                        MaintenanceTask.status == "PENDING"
                    ).first()

                    if not exist_task:
                        task = MaintenanceTask(
                            task_code=f"TSK-{eq.equipment_code}-{today.strftime('%Y%m%d')}",
                            plan_id=fallback_plan_id,
                            equipment_id=eq.id,
                            assigned_tech_id=eq.responsible_engineer_id,
                            plan_version_snapshot=fallback_version,
                            scheduled_date=today,
                            due_date=today + datetime.timedelta(days=3),
                            status="PENDING"
                        )
                        db.add(task)
                        new_tasks_count += 1

                tasks = db.query(MaintenanceTask).filter(
                    MaintenanceTask.equipment_id == eq.id,
                    MaintenanceTask.status == "PENDING",
                    MaintenanceTask.due_date < today
                ).all()
                for t in tasks:
                    t.status = "OVERDUE"
                    t.is_overdue = True

                db.commit()
            except Exception as ex:
                db.rollback()
                logger.error(f"设备 ID={eq.id} 兜底倒计时异常: {str(ex)}")

        return {"updated_equipments": updated_count, "new_tasks": new_tasks_count}
    finally:
        if close_db:
            db.close()