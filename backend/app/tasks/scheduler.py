import threading
import time
import logging
from app.core.database import SessionLocal
from app.tasks.maintenance_cron import run_daily_maintenance_countdown_job
from app.tasks.sla_monitor import run_sla_monitor_job
from app.tasks.file_cleaner import run_orphan_files_cleanup_job

logger = logging.getLogger("maintainwise.scheduler")

class BackgroundSchedulerManager:
    """
    后台守护调度管理器 (用于 Docker 容器生产模式自动启动定时巡检、SLA告警与孤儿文件清理)
    """
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None

    def _worker_loop(self):
        logger.info("MaintainWise 后台调度中心已在独立守护线程中启动")
        last_hourly_run = 0
        last_daily_run = 0

        while not self._stop_event.is_set():
            now = time.time()
            try:
                db = SessionLocal()
                try:
                    # 1. 每 5 分钟轮询 SLA 响应与解决超时 (SWR-FLT-008)
                    run_sla_monitor_job(db)

                    # 2. 每小时检查一次维护到期与派单 (SWR-MNT-004)
                    if now - last_hourly_run >= 3600:
                        run_daily_maintenance_countdown_job(db)
                        last_hourly_run = now

                    # 3. 每日执行一次孤儿文件清理 (SWR-SYS-006)
                    if now - last_daily_run >= 86400:
                        run_orphan_files_cleanup_job(db)
                        last_daily_run = now

                finally:
                    db.close()
            except Exception as e:
                logger.error(f"后台调度任务执行异常: {e}")

            # 睡眠 300 秒 (5分钟)，若收到退出信号立即终止
            self._stop_event.wait(300)

        logger.info("MaintainWise 后台调度中心已安全停止")

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

_global_scheduler = None

def start_background_scheduler():
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = BackgroundSchedulerManager()
        _global_scheduler.start()
    return _global_scheduler
