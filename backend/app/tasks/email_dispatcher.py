import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.equipment import Equipment
from app.models.maintenance import MaintenanceNotifyConfig, MaintenanceNotifyLog
from app.models.user import User
from app.services.email_service import EmailService
import logging

logger = logging.getLogger(__name__)

def run_maintenance_email_dispatch_job(db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    today = datetime.date.today()
    sent_count = 0

    try:
        # 获取开启的通知阶段配置
        configs = db.query(MaintenanceNotifyConfig).filter(MaintenanceNotifyConfig.is_enabled == True).all()
        lead_days_set = {c.lead_days for c in configs}

        equipments = db.query(Equipment).filter(
            Equipment.status.in_(["RUNNING", "MAINTENANCE_PENDING"]),
            Equipment.is_deleted == False
        ).all()

        for eq in equipments:
            if not eq.next_maintenance_date:
                continue

            delta = (eq.next_maintenance_date - today).days
            if delta in lead_days_set:
                # 检查是否已发送过今日该阶段的提醒 (幂等防重)
                exist_log = db.query(MaintenanceNotifyLog).filter(
                    MaintenanceNotifyLog.equipment_id == eq.id,
                    MaintenanceNotifyLog.target_notify_date == today,
                    MaintenanceNotifyLog.notify_stage == delta
                ).first()

                if not exist_log:
                    # 确定收件人
                    recipient = "admin@factory.com"
                    if eq.responsible_engineer_id:
                        eng = db.query(User).filter(User.id == eq.responsible_engineer_id).first()
                        if eng and eng.email:
                            recipient = eng.email

                    # 记录发信日志
                    log = MaintenanceNotifyLog(
                        equipment_id=eq.id,
                        target_notify_date=today,
                        notify_stage=delta,
                        recipient_email=recipient,
                        status="SUCCESS"
                    )
                    db.add(log)
                    sent_count += 1

                    # 调用邮件发送服务
                    try:
                        EmailService.send_email(
                            to_email=recipient,
                            subject=f"【维保到期提醒】设备【{eq.equipment_name}】将于 {delta} 天后到达计划维护期",
                            content=f"尊敬的责任工程师：\n\n设备【{eq.equipment_name}】(编码: {eq.equipment_code}) 下次维护日期为 {eq.next_maintenance_date}，距离今天剩余 {delta} 天，请提前筹备维保物资并按时执行检修保养。",
                            db=db
                        )
                    except Exception as err:
                        logger.warning(f"向 {recipient} 发送维保到期邮件提醒异常: {err}")

        db.commit()
        return {"dispatched_emails": sent_count}
    finally:
        if close_db:
            db.close()
