import os
import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.equipment import EquipmentFile
import logging

logger = logging.getLogger(__name__)

def run_orphan_files_cleanup_job(db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    now = datetime.datetime.now(datetime.timezone.utc)
    expire_threshold = now - datetime.timedelta(hours=24)
    cleaned_count = 0

    try:
        # 查询未关联且创建超过24小时的孤儿文件
        orphans = db.query(EquipmentFile).filter(
            EquipmentFile.is_linked == False,
            EquipmentFile.created_at < expire_threshold
        ).limit(100).all()

        for f in orphans:
            try:
                if os.path.exists(f.storage_path):
                    os.remove(f.storage_path)
                db.delete(f)
                cleaned_count += 1
            except Exception as ex:
                logger.error(f"清理孤儿文件 {f.storage_path} 失败: {str(ex)}")

        db.commit()
        return {"cleaned_files": cleaned_count}
    finally:
        if close_db:
            db.close()
