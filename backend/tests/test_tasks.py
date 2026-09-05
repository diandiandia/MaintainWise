import pytest
import datetime
from app.models.equipment import Equipment, Location, EquipmentFile
from app.models.fault import FaultRecord
from app.models.maintenance import MaintenanceTask, MaintenanceNotifyLog
from app.models.user import User
from app.tasks.maintenance_cron import run_daily_maintenance_countdown_job
from app.tasks.sla_monitor import run_sla_monitor_job
from app.tasks.email_dispatcher import run_maintenance_email_dispatch_job
from app.tasks.file_cleaner import run_orphan_files_cleanup_job

def test_maintenance_countdown_worker(db_session):
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    today = datetime.date.today()

    # 创建一台今天到期的设备
    eq = Equipment(
        equipment_code="DEV-CRON-TEST-001",
        equipment_name="排风机",
        equipment_type="FAN",
        work_type="MECHANICAL",
        location_id=loc.id,
        model_spec="CF-100",
        maintenance_interval_days=30,
        next_maintenance_date=today,
        status="RUNNING"
    )
    db_session.add(eq)
    db_session.commit()

    # 执行每日倒计时扫描调度
    res = run_daily_maintenance_countdown_job(db_session)
    assert res["updated_equipments"] >= 1

    # 验证设备状态跃迁为 MAINTENANCE_PENDING
    db_session.refresh(eq)
    assert eq.status == "MAINTENANCE_PENDING"

    # 验证生成了对应的待办任务
    task = db_session.query(MaintenanceTask).filter(
        MaintenanceTask.equipment_id == eq.id,
        MaintenanceTask.scheduled_date == today
    ).first()
    assert task is not None
    assert task.status == "PENDING"

def test_sla_monitor_worker(db_session):
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    admin = db_session.query(User).filter(User.username == "admin").first()

    # 创建一条40分钟前上报且未接单的 CRITICAL 严重故障
    past_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=45)
    fault = FaultRecord(
        fault_code="FLT-SLA-TEST-001",
        source_type="MANUAL_REPORT",
        equipment_id=1,
        snapshot_location_id=loc.id,
        fault_title="高压配电柜打火",
        fault_desc="高压主进线打火",
        fault_system="ELECTRICAL",
        fault_part="进线断路器",
        severity_level="CRITICAL", # 限时30分钟响应
        status="OPEN",
        reported_by=admin.id,
        reported_at=past_time,
        is_sla_response_breached=False
    )
    db_session.add(fault)
    db_session.commit()

    # 执行 SLA 轮询监控
    res = run_sla_monitor_job(db_session)
    assert res["breached_faults"] >= 1

    db_session.refresh(fault)
    assert fault.is_sla_response_breached is True

def test_email_dispatch_dedup(db_session):
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    today = datetime.date.today()

    # 创建一台距离维护还有 3 天的设备
    eq = Equipment(
        equipment_code="DEV-EMAIL-DEDUP-001",
        equipment_name="循环电机",
        equipment_type="MOTOR",
        work_type="ELECTRICAL",
        location_id=loc.id,
        model_spec="Y100",
        next_maintenance_date=today + datetime.timedelta(days=3),
        status="RUNNING"
    )
    db_session.add(eq)
    db_session.commit()

    # 首次执行发信调度 -> 应当发信成功
    res1 = run_maintenance_email_dispatch_job(db_session)
    assert res1["dispatched_emails"] >= 1

    # 紧接着执行第二次发信调度 -> 应当被幂等防重拦截，发信数为0
    res2 = run_maintenance_email_dispatch_job(db_session)
    assert res2["dispatched_emails"] == 0

def test_orphan_file_cleaner(db_session, tmp_path):
    # 创建一个临时孤儿文件
    fake_file = tmp_path / "orphan_test.txt"
    fake_file.write_text("dummy content")

    # 创建时间模拟为 25 小时前
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=25)
    file_record = EquipmentFile(
        file_tag="OTHER",
        original_filename="orphan_test.txt",
        storage_path=str(fake_file),
        file_size_bytes=13,
        mime_type="text/plain",
        file_sha256="12345",
        is_linked=False,
        created_at=past
    )
    db_session.add(file_record)
    db_session.commit()

    # 运行清理任务
    res = run_orphan_files_cleanup_job(db_session)
    assert res["cleaned_files"] >= 1
    assert not fake_file.exists()
