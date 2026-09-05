import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.equipment import Equipment
from app.models.maintenance import MaintenanceTask
import logging

logger = logging.getLogger(__name__)

def run_daily_maintenance_countdown_job(db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    today = datetime.date.today()
    chunk_size = 100
    offset = 0
    updated_count = 0
    new_tasks_count = 0

    try:
        while True:
            equipments = db.query(Equipment).filter(
                Equipment.status.in_(["RUNNING", "MAINTENANCE_PENDING"]),
                Equipment.is_deleted == False
            ).order_by(Equipment.id).offset(offset).limit(chunk_size).all()

            if not equipments:
                break

            for eq in equipments:
                try:
                    if eq.next_maintenance_date is None:
                        continue

                    delta_days = (eq.next_maintenance_date - today).days

                    # 1. 倒计时到期：状态跃迁并派发工单
                    if delta_days <= 0 and eq.status == "RUNNING":
                        eq.status = "MAINTENANCE_PENDING"
                        updated_count += 1

                        # 防重复生成今日待办
                        exist_task = db.query(MaintenanceTask).filter(
                            MaintenanceTask.equipment_id == eq.id,
                            MaintenanceTask.scheduled_date == today,
                            MaintenanceTask.status == "PENDING"
                        ).first()

                        if not exist_task:
                            task = MaintenanceTask(
                                task_code=f"TSK-{eq.equipment_code}-{today.strftime('%Y%m%d')}",
                                plan_id=1,
                                equipment_id=eq.id,
                                assigned_tech_id=eq.responsible_engineer_id,
                                plan_version_snapshot="V1.0",
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

            offset += chunk_size

        return {"updated_equipments": updated_count, "new_tasks": new_tasks_count}
    finally:
        if close_db:
            db.close()
