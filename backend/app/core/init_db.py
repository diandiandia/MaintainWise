from sqlalchemy.orm import Session
from app.core.database import Base, engine, SessionLocal
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.equipment import Location, Equipment, EquipmentParam, EquipmentFile
from app.models.maintenance import MaintenancePlan, MaintenancePlanItem, MaintenanceTask, InspectionRecord, InspectionRecordDetail, MaintenanceNotifyConfig, MaintenanceNotifyLog
from app.models.fault import FaultRecord, SparePart
from app.models.knowledge import KnowledgeArticle
from app.models.training import TrainingCourse, TrainingCourseCase, TrainingRecord, TrainingUserScore
from app.models.system import SystemSmtpConfig
import logging

logger = logging.getLogger(__name__)

def init_db(db: Session = None):
    # 自动创建所有表结构
    Base.metadata.create_all(bind=engine)
    
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
        
    try:
        # 1. 种子数据：默认超级管理员 (admin)
        admin_user = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()
        if not admin_user:
            admin_user = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                full_name=settings.DEFAULT_ADMIN_NAME,
                employee_no=settings.DEFAULT_ADMIN_EMPLOYEE_NO,
                email=settings.DEFAULT_ADMIN_EMAIL,
                phone="13800000000",
                role_code="ADMIN",
                work_type="GENERAL",
                is_active=True,
                force_change_password=True # 首次登录强制改密
            )
            db.add(admin_user)
            db.commit()
            logger.info("默认超级管理员账号 admin 初始化成功！")
            
        # 2. 种子数据：默认层级拓扑树节点 (3级: 工厂 -> 部门 -> 系统，第4级为设备信息)
        root_loc = db.query(Location).filter(Location.location_code == "LOC-FAC-01").first()
        if not root_loc:
            loc1 = Location(id=1, parent_id=None, location_name="总装制造工厂", location_code="LOC-FAC-01", level_depth=1, node_type="FACTORY", tree_path="/1/", is_leaf=False, sort_order=1)
            loc2 = Location(id=2, parent_id=1, location_name="智能制造运维部", location_code="LOC-DEP-01", level_depth=2, node_type="DEPARTMENT", tree_path="/1/2/", is_leaf=False, sort_order=1)
            loc3 = Location(id=3, parent_id=2, location_name="主排风动力循环系统", location_code="LOC-SYS-01", level_depth=3, node_type="SYSTEM", tree_path="/1/2/3/", is_leaf=True, sort_order=1)
            db.add_all([loc1, loc2, loc3])
            db.commit()
            logger.info("默认3级层级拓扑分类树初始化成功 (工厂->部门->系统)！")
            
        # 3. 种子数据：默认维护到期提醒规则 (提前 7, 3, 1 天及当天)
        for lead in [7, 3, 1, 0]:
            cfg = db.query(MaintenanceNotifyConfig).filter(MaintenanceNotifyConfig.lead_days == lead).first()
            if not cfg:
                db.add(MaintenanceNotifyConfig(lead_days=lead, is_enabled=True, target_role_group="ALL"))
        db.commit()

        # 4. 种子数据：默认 SMTP 邮件服务器配置 (SWR-SYS-001)
        smtp_cfg = db.query(SystemSmtpConfig).first()
        if not smtp_cfg:
            smtp_cfg = SystemSmtpConfig(
                smtp_host="smtp.maintainwise.com",
                smtp_port=465,
                smtp_user="noreply@maintainwise.com",
                smtp_pass="InitialSmtpAuth2026",
                sender_name="MaintainWise 智能运维中心",
                use_ssl=True,
                use_tls=False,
                is_active=True
            )
            db.add(smtp_cfg)
            db.commit()
            logger.info("默认 SMTP 邮件服务器配置初始化成功！")
        
    finally:
        if close_db:
            db.close()

if __name__ == "__main__":
    init_db()
    print("数据库结构与种子数据初始化全部完成！")