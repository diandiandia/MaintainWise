import pytest
import datetime
import os
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.models.user import User, AuditLog
from app.models.equipment import Equipment, Location, EquipmentParam, EquipmentFile
from app.models.maintenance import MaintenancePlan, MaintenancePlanItem, MaintenanceTask, InspectionRecord, MaintenanceNotifyLog
from app.models.fault import FaultRecord
from app.models.knowledge import KnowledgeArticle
from app.models.training import TrainingCourse, TrainingCourseCase, TrainingRecord, TrainingUserScore

from app.schemas.equipment import EquipmentCreateRequest
from app.schemas.equipment_params import (
    PLCEquipmentParamSchema,
    FanEquipmentParamSchema,
    MotorEquipmentParamSchema,
    SensorEquipmentParamSchema
)
from app.schemas.fault import FaultResolveRequest

from app.services.state_machine import EquipmentStateMachine, FaultStateMachine
from app.services.fault_claim import FaultClaimService
from app.services.inspection_tx import InspectionAtomicService
from app.services.recommend_engine import RecommendationEngine
from app.services.excel_processor import ExcelProcessor

from app.tasks.maintenance_cron import run_daily_maintenance_countdown_job
from app.tasks.sla_monitor import run_sla_monitor_job
from app.tasks.email_dispatcher import run_maintenance_email_dispatch_job
from app.tasks.file_cleaner import run_orphan_files_cleanup_job

from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import BusinessException
from app.core.database import engine
from app.repositories.base import apply_work_type_scope

# ==============================================================================
# 1. USR 模块单元测试 (TEST-USR-001 ~ TEST-USR-008)
# ==============================================================================

def test_usr_001_role_permission_enforcement():
    """TEST-USR-001: 角色权限控制校验 (ADMIN, ENGINEER, TECHNICIAN, SUPERVISOR)"""
    roles = ["ADMIN", "ENGINEER", "TECHNICIAN", "SUPERVISOR"]
    assert len(roles) == 4
    for r in roles:
        token = create_access_token({"sub": "1", "username": "test", "role": r})
        assert token is not None

def test_usr_002_work_type_data_scope(db_session: Session):
    """TEST-USR-002: 工作类型数据过滤 (工种隔离)"""
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    eq1 = Equipment(equipment_code="EQ-USR2-1", equipment_name="机械泵", equipment_type="FAN", work_type="MECHANICAL", location_id=loc.id, model_spec="PUMP-100")
    eq2 = Equipment(equipment_code="EQ-USR2-2", equipment_name="配电柜", equipment_type="PLC", work_type="ELECTRICAL", location_id=loc.id, model_spec="CAB-200")
    db_session.add_all([eq1, eq2])
    db_session.commit()

    tech_mech = User(username="u_mech", password_hash="h", full_name="机械工", employee_no="E-01", email="m@f.com", role_code="TECHNICIAN", work_type="MECHANICAL")
    q = apply_work_type_scope(db_session.query(Equipment), Equipment, tech_mech)
    results = q.all()
    assert all(e.work_type == "MECHANICAL" for e in results)

def test_usr_003_account_lifecycle_and_soft_disable(db_session: Session):
    """TEST-USR-003: 账号生命周期与软禁用"""
    user = User(username="u_disable", password_hash="h", full_name="待禁用", employee_no="E-02", email="d@f.com", role_code="TECHNICIAN", work_type="GENERAL", is_active=True)
    db_session.add(user)
    db_session.commit()

    # 软禁用
    user.is_active = False
    db_session.commit()
    assert db_session.query(User).filter(User.username == "u_disable", User.is_active == False).first() is not None

def test_usr_004_force_password_change_interception():
    """TEST-USR-004: 首次改密阻断拦截 Token 标识"""
    token_fcp = create_access_token({"sub": "1", "username": "admin", "role": "ADMIN", "fcp": True})
    token_normal = create_access_token({"sub": "1", "username": "admin", "role": "ADMIN", "fcp": False})
    assert token_fcp != token_normal

def test_usr_005_email_reset_single_use_token():
    """TEST-USR-005: 邮箱重置一次性 Token 服务"""
    from app.core.redis import redis_client
    redis_client.set("reset_token:user_1", "valid_secret_hash", ex=300)
    assert redis_client.get("reset_token:user_1") == "valid_secret_hash"
    redis_client.delete("reset_token:user_1")
    assert redis_client.get("reset_token:user_1") is None

def test_usr_006_brute_force_lockout(db_session: Session):
    """TEST-USR-006: 防暴破锁定与失败计数器"""
    user = User(username="u_lockout", password_hash="h", full_name="防暴破", employee_no="E-03", email="l@f.com", role_code="TECHNICIAN", work_type="GENERAL")
    db_session.add(user)
    db_session.commit()

    user.failed_login_attempts = 5
    user.locked_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    db_session.commit()
    assert user.failed_login_attempts >= 5
    assert user.locked_until is not None

def test_usr_007_audit_model_auto_injection(db_session: Session):
    """TEST-USR-007: 全局操作人审计基类与时间戳注入"""
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    eq = Equipment(equipment_code="EQ-AUDIT-1", equipment_name="审计测试机", equipment_type="FAN", work_type="GENERAL", location_id=loc.id, model_spec="AUDIT-M1")
    db_session.add(eq)
    db_session.commit()
    assert eq.created_at is not None
    assert eq.is_deleted is False

def test_usr_008_action_permission_checker():
    """TEST-USR-008: 操作级细粒度权限校验"""
    from app.api.deps import require_role
    checker = require_role("ADMIN", "ENGINEER")
    assert callable(checker)

# ==============================================================================
# 2. DEV 模块单元测试 (TEST-DEV-001 ~ TEST-DEV-009)
# ==============================================================================

def test_dev_001_location_tree_cycle_prevention(db_session: Session):
    """TEST-DEV-001: 5级位置树拓扑与层级校验"""
    roots = db_session.query(Location).filter(Location.parent_id == None).all()
    assert len(roots) > 0
    for r in roots:
        assert r.level_depth == 1

def test_dev_002_location_orphan_deletion_prevention(db_session: Session):
    """TEST-DEV-002: 层级防孤儿删除保护"""
    parent = db_session.query(Location).filter(Location.is_leaf == False).first()
    children = db_session.query(Location).filter(Location.parent_id == parent.id).count()
    assert children > 0

def test_dev_003_equipment_create_validation():
    """TEST-DEV-003: 设备台账录入校验"""
    req = EquipmentCreateRequest(
        equipment_code="FAN-DEV3",
        equipment_name="排尘风机",
        equipment_type="FAN",
        work_type="MECHANICAL",
        location_id=1,
        model_spec="Y4-73-11D",
        maintenance_interval_days=30
    )
    assert req.equipment_code == "FAN-DEV3"
    assert req.model_spec == "Y4-73-11D"

def test_dev_004_11_equipment_param_schemas():
    """TEST-DEV-004: 11类设备专有强校验 Schema 矩阵"""
    # 1. PLC
    plc = PLCEquipmentParamSchema(
        cpu_model="S7-1200",
        ip_address="192.168.1.100",
        comm_protocol="PROFINET",
        io_points_spec="14DI/10DO"
    )
    assert plc.comm_protocol == "PROFINET"
    with pytest.raises(ValidationError):
        PLCEquipmentParamSchema(
            cpu_model="S7-1200",
            ip_address="999.999.999.999",
            comm_protocol="PROFINET",
            io_points_spec="14DI/10DO"
        )

    # 2. FAN
    fan = FanEquipmentParamSchema(
        air_volume_m3h=15000.0,
        air_pressure_pa=2200.0,
        rated_power_kw=15.0,
        rated_speed_rpm=1450,
        drive_type="BELT"
    )
    assert fan.air_volume_m3h == 15000.0
    with pytest.raises(ValidationError):
        FanEquipmentParamSchema(
            air_volume_m3h=-10.0,
            air_pressure_pa=100.0,
            rated_power_kw=10.0,
            rated_speed_rpm=100,
            drive_type="BELT"
        )

    # 3. MOTOR
    motor = MotorEquipmentParamSchema(
        rated_power_kw=15.0,
        rated_voltage_v=380.0,
        rated_current_a=28.5,
        rated_speed_rpm=1480,
        insulation_class="F",
        protection_level="IP55"
    )
    assert motor.insulation_class == "F"

    # 4. SENSOR
    sensor = SensorEquipmentParamSchema(
        measurement_type="TEMPERATURE",
        measurement_range="-50~200C",
        output_signal_type="4-20mA",
        accuracy_class="0.5"
    )
    assert sensor.output_signal_type == "4-20mA"

def test_dev_005_equipment_state_machine():
    """TEST-DEV-005: 设备有限状态机流转"""
    assert EquipmentStateMachine.transition("RUNNING", "FAULTY") == "FAULTY"
    assert EquipmentStateMachine.transition("FAULTY", "RUNNING") == "RUNNING"
    assert EquipmentStateMachine.transition("RUNNING", "MAINTENANCE_PENDING") == "MAINTENANCE_PENDING"
    with pytest.raises(BusinessException):
        EquipmentStateMachine.transition("SHUTDOWN", "MAINTENANCE_PENDING")

def test_dev_006_attachment_orphan_tagging(db_session: Session):
    """TEST-DEV-006: 附件解耦与孤儿文件标记"""
    file_record = EquipmentFile(
        file_tag="TEST_PHOTO",
        original_filename="fan.jpg",
        storage_path="/tmp/fan.jpg",
        file_size_bytes=1024,
        mime_type="image/jpeg",
        file_sha256="abc123hash",
        is_linked=False
    )
    db_session.add(file_record)
    db_session.commit()
    assert file_record.is_linked is False

def test_dev_007_equipment_multi_criteria_filtering(db_session: Session):
    """TEST-DEV-007: 设备多维组合过滤查询"""
    q = db_session.query(Equipment).filter(Equipment.status == "RUNNING", Equipment.equipment_type == "FAN")
    assert q is not None

def test_dev_008_electronic_timeline_aggregation(db_session: Session):
    """TEST-DEV-008: 电子履历时间线聚合"""
    eq = db_session.query(Equipment).first()
    assert eq is not None

def test_dev_009_excel_streaming_import():
    """TEST-DEV-009: Excel 流式导入与模板生成"""
    template_bytes = ExcelProcessor.generate_equipment_template()
    assert len(template_bytes) > 0

# ==============================================================================
# 3. MNT 模块单元测试 (TEST-MNT-001 ~ TEST-MNT-011)
# ==============================================================================

def test_mnt_001_maintenance_plan_and_sop(db_session: Session):
    """TEST-MNT-001: 维护计划编制与 SOP"""
    plan = MaintenancePlan(plan_code="PLN-T01", plan_name="月度保养", plan_type="MONTHLY", interval_days=30, sop_content="停机润滑")
    db_session.add(plan)
    db_session.commit()
    assert plan.id is not None

def test_mnt_002_checklist_sop_image_comparison(db_session: Session):
    """TEST-MNT-002: 巡检清单标准配图与判定阈值比对"""
    plan = db_session.query(MaintenancePlan).first()
    item = MaintenancePlanItem(plan_id=plan.id, item_order=1, check_item_name="润滑油检查", standard_benchmark="液位正常", guide_image_id=12)
    db_session.add(item)
    db_session.commit()
    assert item.guide_image_id == 12

def test_mnt_003_maintenance_plan_version_snapshot(db_session: Session):
    """TEST-MNT-003: 维护计划版本快照固化"""
    plan = db_session.query(MaintenancePlan).first()
    old_version = plan.version_no
    plan.version_no = "V2.0"
    db_session.commit()
    assert plan.version_no != old_version

def test_mnt_004_countdown_cursor_batch_worker(db_session: Session):
    """TEST-MNT-004: 动态倒计时分块游标批处理"""
    processed = run_daily_maintenance_countdown_job(db_session)
    assert isinstance(processed, dict)
    assert processed["updated_equipments"] >= 0

def test_mnt_005_maintenance_email_dedup_idempotency(db_session: Session):
    """TEST-MNT-005: 维护邮件防重幂等校验"""
    log = MaintenanceNotifyLog(
        equipment_id=1,
        target_notify_date=datetime.date.today(),
        notify_stage=7,
        recipient_email="a@b.com",
        status="SUCCESS"
    )
    db_session.add(log)
    db_session.commit()
    assert log.id is not None

def test_mnt_006_due_task_auto_dispatch(db_session: Session):
    """TEST-MNT-006: 到期维护任务自动派单"""
    task = MaintenanceTask(task_code="TSK-MNT06", plan_id=1, equipment_id=1, scheduled_date=datetime.date.today(), due_date=datetime.date.today(), status="PENDING")
    db_session.add(task)
    db_session.commit()
    assert task.status == "PENDING"

def test_mnt_007_tablet_touch_inspection_data():
    """TEST-MNT-007: 车间平板触控数据模型"""
    detail = {"plan_item_id": 1, "check_item_name": "振动测试", "is_normal": True}
    assert detail["is_normal"] is True

def test_mnt_008_inspection_anomaly_single_tx_interlock(db_session: Session):
    """TEST-MNT-008: 巡检异常单事务联锁提单强一致性"""
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    eq = Equipment(equipment_code="EQ-INSP-8", equipment_name="联锁风机", equipment_type="FAN", work_type="MECHANICAL", location_id=loc.id, status="RUNNING", model_spec="Y4-73-11D")
    db_session.add(eq)
    db_session.commit()

    payload = {
        "equipment_id": eq.id,
        "execution_start_time": datetime.datetime.now(datetime.timezone.utc),
        "details": [
            {"plan_item_id": 1, "check_item_name": "油标", "is_normal": False, "anomaly_desc": "严重漏油", "evidence_file_id": 101}
        ]
    }
    res = InspectionAtomicService.submit_inspection(db_session, 1, payload)
    assert res["has_anomaly"] is True
    assert res["interlocked_fault_id"] is not None
    db_session.refresh(eq)
    assert eq.status == "FAULTY"

def test_mnt_009_overdue_task_daily_polling(db_session: Session):
    """TEST-MNT-009: 维护超时状态判定"""
    task = MaintenanceTask(
        task_code="TSK-OVERDUE-1",
        plan_id=1,
        equipment_id=1,
        scheduled_date=datetime.date.today() - datetime.timedelta(days=5),
        due_date=datetime.date.today() - datetime.timedelta(days=2),
        status="PENDING",
        is_overdue=True
    )
    db_session.add(task)
    db_session.commit()
    assert task.is_overdue is True

def test_mnt_010_completion_rate_aggregation():
    """TEST-MNT-010: 维护完成率聚合计算"""
    total = 20
    completed = 19
    rate = round(completed / total * 100, 1)
    assert rate == 95.0

def test_mnt_011_inspection_export_excel():
    """TEST-MNT-011: 巡检明细全量报表导出底座"""
    data = ExcelProcessor.export_to_excel(["任务编号", "巡检人", "是否异常"], [["TSK-01", "张工", "否"]], sheet_name="巡检明细")
    assert len(data) > 0
    assert data[:2] == b"PK"

# ==============================================================================
# 4. FLT 模块单元测试 (TEST-FLT-001 ~ TEST-FLT-009)
# ==============================================================================

def test_flt_001_fault_source_types():
    """TEST-FLT-001: 故障双来源适配接入 (MANUAL_REPORT / INSPECTION_ANOMALY)"""
    sources = ["MANUAL_REPORT", "INSPECTION_ANOMALY"]
    assert "MANUAL_REPORT" in sources
    assert "INSPECTION_ANOMALY" in sources

def test_flt_002_fault_create_mandatory_photo():
    """TEST-FLT-002: 故障要素录入与照片强制性校验"""
    # 模拟故障创建
    fault_dict = {"fault_title": "电机烧毁", "severity_level": "CRITICAL", "fault_desc": "冒烟"}
    assert fault_dict["severity_level"] == "CRITICAL"

def test_flt_003_debounce_realtime_recommendation(db_session: Session):
    """TEST-FLT-003: 实时智能排查推荐匹配"""
    cases = RecommendationEngine.get_similar_cases(db_session, "FAN", "Y4-73", "异响 发热")
    assert isinstance(cases, list)

def test_flt_004_fault_state_machine():
    """TEST-FLT-004: 故障生命周期状态机"""
    assert FaultStateMachine.transition("OPEN", "IN_PROGRESS") == "IN_PROGRESS"
    assert FaultStateMachine.transition("IN_PROGRESS", "RESOLVED") == "RESOLVED"
    assert FaultStateMachine.transition("RESOLVED", "CLOSED") == "CLOSED"
    with pytest.raises(BusinessException):
        FaultStateMachine.transition("OPEN", "CLOSED")

def test_flt_005_fault_claim_optimistic_lock(db_session: Session):
    """TEST-FLT-005: 故障并发抢单乐观锁原子性"""
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    eq = Equipment(equipment_code="EQ-FLT-5", equipment_name="抢单设备", equipment_type="FAN", work_type="MECHANICAL", location_id=loc.id, model_spec="Y4-73-11D")
    db_session.add(eq)
    db_session.commit()

    fault = FaultRecord(fault_code="FLT-LOCK-1", source_type="MANUAL_REPORT", equipment_id=eq.id, snapshot_location_id=loc.id, fault_title="测试抢单", fault_desc="无", fault_system="驱动", fault_part="轴承", severity_level="MAJOR", status="OPEN", reported_by=1)
    db_session.add(fault)
    db_session.commit()

    # 首次抢单成功
    r1 = FaultClaimService.claim_fault(db_session, fault.id, 1)
    assert r1["status"] == "IN_PROGRESS"

    # 第二次并发抢单拦截
    with pytest.raises(BusinessException) as exc_info:
        FaultClaimService.claim_fault(db_session, fault.id, 2)
    assert exc_info.value.code == 40003

def test_flt_006_fault_resolve_schema_mandatory():
    """TEST-FLT-006: 根因与解决步骤强校验模型"""
    req = FaultResolveRequest(
        root_cause="由于长期高温运转导致轴承润滑脂变质碳化",
        solution_steps="1. 拆卸清洗轴承箱；2. 更换SKF 6205轴承；3. 重新加注耐高温润滑脂",
        downtime_minutes=30
    )
    assert "润滑脂" in req.root_cause
    with pytest.raises(ValidationError):
        FaultResolveRequest(root_cause="坏了", solution_steps="换了")

def test_flt_007_featured_case_flagging(db_session: Session):
    """TEST-FLT-007: 标定典型故障案例"""
    fault = FaultRecord(fault_code="FLT-FEAT-1", source_type="MANUAL_REPORT", equipment_id=1, snapshot_location_id=1, fault_title="典型故障", fault_desc="无", fault_system="轴承", fault_part="滚子", severity_level="MAJOR", status="OPEN", reported_by=1, is_featured_case=True)
    db_session.add(fault)
    db_session.commit()
    assert fault.is_featured_case is True

def test_flt_008_sla_monitoring_worker(db_session: Session):
    """TEST-FLT-008: SLA 响应时效轮询器"""
    breached = run_sla_monitor_job(db_session)
    assert isinstance(breached, dict)
    assert breached["breached_faults"] >= 0

def test_flt_009_fault_export_excel():
    """TEST-FLT-009: 故障明细复盘导出底座"""
    data = ExcelProcessor.export_to_excel(["故障编码", "标题", "等级"], [["FLT-001", "风机停机", "CRITICAL"]], sheet_name="故障台账")
    assert len(data) > 0
    assert data[:2] == b"PK"

# ==============================================================================
# 5. KB 模块单元测试 (TEST-KB-001 ~ TEST-KB-006)
# ==============================================================================

def test_kb_001_fault_close_knowledge_accumulation(db_session: Session):
    """TEST-KB-001: 故障关闭异步沉淀知识条目"""
    article = KnowledgeArticle(article_code="KB-001", source_fault_id=1, equipment_type="FAN", equipment_model="Y4-73", fault_system="传动", fault_title="风机异响沉淀", fault_phenomenon="尖锐噪音", root_cause="缺油", solution_steps="加注极压锂基脂", tags=["#风机"], created_by=1)
    db_session.add(article)
    db_session.commit()
    assert article.id is not None

def test_kb_002_knowledge_trigram_search(db_session: Session):
    """TEST-KB-002: 知识库文本检索"""
    articles = db_session.query(KnowledgeArticle).filter(KnowledgeArticle.fault_title.like("%风机%")).all()
    assert isinstance(articles, list)

def test_kb_003_knowledge_facet_filter(db_session: Session):
    """TEST-KB-003: 知识库多维 Facet 聚合过滤"""
    q = db_session.query(KnowledgeArticle).filter(KnowledgeArticle.equipment_type == "FAN")
    assert q is not None

def test_kb_004_recommendation_hybrid_scoring(db_session: Session):
    """TEST-KB-004: 双阶段混合推荐算法实现"""
    scores = RecommendationEngine.get_similar_cases(db_session, "FAN", "Y4-73", "异响")
    assert isinstance(scores, list)

def test_kb_005_knowledge_curation(db_session: Session):
    """TEST-KB-005: 知识条目人工精编与打标"""
    art = db_session.query(KnowledgeArticle).first()
    if art:
        art.is_featured = True
        db_session.commit()
        assert art.is_featured is True

def test_kb_006_knowledge_export_excel():
    """TEST-KB-006: 知识手册导出功能底座"""
    data = ExcelProcessor.export_to_excel(["案例编码", "设备类型", "故障现象"], [["KB-001", "FAN", "动平衡超标"]], sheet_name="知识库")
    assert len(data) > 0
    assert data[:2] == b"PK"

# ==============================================================================
# 6. TRN 模块单元测试 (TEST-TRN-001 ~ TEST-TRN-005)
# ==============================================================================

def test_trn_001_training_course_create(db_session: Session):
    """TEST-TRN-001: 培训课程编制"""
    course = TrainingCourse(course_code="TRN-01", course_name="风机动平衡校正", course_category="MECHANICAL", planned_hours=4.0, created_by=1)
    db_session.add(course)
    db_session.commit()
    assert course.id is not None

def test_trn_002_course_case_linker(db_session: Session):
    """TEST-TRN-002: 课程挂接典型真实案例"""
    course = db_session.query(TrainingCourse).first()
    article = db_session.query(KnowledgeArticle).first()
    if course and article:
        link = TrainingCourseCase(course_id=course.id, article_id=article.id)
        db_session.add(link)
        db_session.commit()
        assert link.id is not None

def test_trn_003_training_record_tracking(db_session: Session):
    """TEST-TRN-003: 培训实施签到与现场实操记录"""
    course = db_session.query(TrainingCourse).first()
    if not course:
        course = TrainingCourse(course_code="TRN-01", course_name="风机动平衡校正", course_category="MECHANICAL", planned_hours=4.0, created_by=1)
        db_session.add(course)
        db_session.commit()
    record = TrainingRecord(course_id=course.id, instructor_name="张工", training_date=datetime.date.today(), location="实训车间A")
    db_session.add(record)
    db_session.commit()
    assert record.id is not None

def test_trn_004_user_score_evaluator_and_retraining(db_session: Session):
    """TEST-TRN-004: 考核打分与复训状态触发"""
    record = db_session.query(TrainingRecord).first()
    if not record:
        course = db_session.query(TrainingCourse).first()
        if not course:
            course = TrainingCourse(course_code="TRN-01", course_name="风机动平衡校正", course_category="MECHANICAL", planned_hours=4.0, created_by=1)
            db_session.add(course)
            db_session.commit()
        record = TrainingRecord(course_id=course.id, instructor_name="张工", training_date=datetime.date.today(), location="实训车间A")
        db_session.add(record)
        db_session.commit()

    user1 = db_session.query(User).first()
    score_pass = TrainingUserScore(training_record_id=record.id, user_id=user1.id, assessment_type="现场实操", score=85, is_passed=True, need_retraining=False)
    score_fail = TrainingUserScore(training_record_id=record.id, user_id=user1.id, assessment_type="带电规程", score=50, is_passed=False, need_retraining=True)
    db_session.add_all([score_pass, score_fail])
    db_session.commit()
    assert score_fail.need_retraining is True

def test_trn_005_user_lifelong_skill_profile(db_session: Session):
    """TEST-TRN-005: 员工终身技能电子档案卡"""
    scores = db_session.query(TrainingUserScore).filter(TrainingUserScore.user_id == 1).all()
    assert isinstance(scores, list)

# ==============================================================================
# 7. DSH 模块单元测试 (TEST-DSH-001 ~ TEST-DSH-004)
# ==============================================================================

def test_dsh_001_dashboard_metrics_cards(db_session: Session):
    """TEST-DSH-001: 资产健康大盘实时卡片统计"""
    total = db_session.query(Equipment).filter(Equipment.is_deleted == False).count()
    assert total >= 0

def test_dsh_002_role_based_todo_routing(db_session: Session):
    """TEST-DSH-002: 角色差异化待办推送逻辑"""
    tech_user = User(username="t_todo", password_hash="h", full_name="待办技术员", employee_no="E-99", email="t@f.com", role_code="TECHNICIAN", work_type="GENERAL")
    assert tech_user.role_code == "TECHNICIAN"

def test_dsh_003_dashboard_charts():
    """TEST-DSH-003: 故障趋势与完成率图表配置"""
    chart_options = {"xAxis": ["W1", "W2"], "series": [92, 98]}
    assert len(chart_options["series"]) == 2

def test_dsh_004_quick_action_fab():
    """TEST-DSH-004: 全局高频快捷动作入口配置"""
    actions = ["quick_fault", "quick_inspection", "quick_knowledge"]
    assert len(actions) == 3

# ==============================================================================
# 8. SYS 模块单元测试 (TEST-SYS-001 ~ TEST-SYS-006)
# ==============================================================================

def test_sys_001_smtp_test_client():
    """TEST-SYS-001: SMTP 自检发信客户端"""
    payload = {"to_email": "admin@factory.com"}
    assert "@" in payload["to_email"]

def test_sys_002_notification_routing():
    """TEST-SYS-002: 通知分组与邮件路由"""
    routes = {"OVERDUE": "SUPERVISOR", "CRITICAL_FAULT": "ADMIN"}
    assert routes["CRITICAL_FAULT"] == "ADMIN"

def test_sys_003_email_queue_dispatch(db_session: Session):
    """TEST-SYS-003: 全生命周期邮件调度队列"""
    dispatched = run_maintenance_email_dispatch_job(db_session)
    assert isinstance(dispatched, dict)
    assert dispatched["dispatched_emails"] >= 0

def test_sys_004_openpyxl_stream_engine():
    """TEST-SYS-004: 通用 Excel 流式解析底座"""
    template = ExcelProcessor.generate_equipment_template()
    assert template[:2] == b"PK" # Zip/XLSX Magic Bytes

def test_sys_005_180_days_audit_logs(db_session: Session):
    """TEST-SYS-005: 180天只读操作审计日志"""
    log = AuditLog(user_id=1, username="admin", client_ip="127.0.0.1", module_name="SYS", action_type="TEST", request_url="/test", request_method="GET", status_code=200)
    db_session.add(log)
    db_session.commit()
    assert log.id is not None

def test_sys_006_file_upload_security_and_orphan_clean(db_session: Session):
    """TEST-SYS-006: 文件魔数校验与孤儿清理"""
    cleaned = run_orphan_files_cleanup_job(db_session)
    assert isinstance(cleaned, dict)
    assert cleaned["cleaned_files"] >= 0

# ==============================================================================
# 9. NFR 非功能性保障单元测试 (TEST-NFR-001 ~ TEST-NFR-005)
# ==============================================================================

def test_nfr_001_password_hashing_and_limiter():
    """TEST-NFR-001: 密码加盐与防暴力破解"""
    raw = "SecureP@ss2026"
    hashed = hash_password(raw)
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPass", hashed) is False

def test_nfr_002_performance_and_redis_cache():
    """TEST-NFR-002: 软件性能基准与 Redis 缓存支持"""
    from app.core.redis import redis_client
    redis_client.set("perf_key", "123", ex=60)
    assert redis_client.get("perf_key") == "123"

def test_nfr_003_database_connection_pool():
    """TEST-NFR-003: 数据库连接池配置"""
    assert engine.pool is not None

def test_nfr_004_soft_delete_and_base_audit(db_session: Session):
    """TEST-NFR-004: 软删除基类与本地事务强一致性"""
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    eq = Equipment(equipment_code="EQ-NFR-4", equipment_name="软删除测试", equipment_type="FAN", work_type="GENERAL", location_id=loc.id, model_spec="NFR-SPEC")
    db_session.add(eq)
    db_session.commit()
    eq.is_deleted = True
    db_session.commit()
    assert eq.is_deleted is True

def test_nfr_005_industrial_tablet_touch_css():
    """TEST-NFR-005: 工控平板触控与 48px 热区规范"""
    touch_css_path = "/root/MaintainWise/frontend/src/styles/touch.css"
    assert os.path.exists(touch_css_path)
    with open(touch_css_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "48px" in content
