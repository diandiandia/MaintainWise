import pytest
from app.models.user import User
from app.models.equipment import Location, Equipment, EquipmentFile
from app.models.fault import FaultRecord
from app.models.knowledge import KnowledgeArticle
from app.services.state_machine import EquipmentStateMachine, FaultStateMachine
from app.services.inspection_tx import InspectionAtomicService
from app.services.fault_claim import FaultClaimService
from app.services.recommend_engine import RecommendationEngine
from app.services.excel_processor import ExcelProcessor
from app.core.exceptions import BusinessException

def test_equipment_state_machine():
    assert EquipmentStateMachine.transition("RUNNING", "MAINTENANCE_PENDING") == "MAINTENANCE_PENDING"
    assert EquipmentStateMachine.transition("MAINTENANCE_PENDING", "FAULTY") == "FAULTY"
    with pytest.raises(BusinessException) as exc:
        EquipmentStateMachine.transition("SCRAPPED", "RUNNING") # 报废终态不可逆
    assert exc.value.code == 20005

def test_fault_state_machine():
    assert FaultStateMachine.transition("OPEN", "IN_PROGRESS") == "IN_PROGRESS"
    assert FaultStateMachine.transition("IN_PROGRESS", "RESOLVED") == "RESOLVED"
    with pytest.raises(BusinessException) as exc:
        FaultStateMachine.transition("OPEN", "CLOSED") # 必须经由处理和解决
    assert exc.value.code == 40002

def test_inspection_tx_anomaly_with_missing_photo(db_session):
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    admin = db_session.query(User).filter(User.username == "admin").first()
    eq = Equipment(
        equipment_code="DEV-INSP-ERR-001",
        equipment_name="离心风机",
        equipment_type="FAN",
        work_type="MECHANICAL",
        location_id=loc.id,
        model_spec="CF-500",
        status="RUNNING"
    )
    db_session.add(eq)
    db_session.commit()

    # 提交异常但未传照片 -> 应当抛出 30002
    payload = {
        "equipment_id": eq.id,
        "details": [{
            "plan_item_id": 1,
            "check_item_name": "轴承润滑状态",
            "is_normal": False,
            "anomaly_desc": "严重缺油异响",
            "evidence_file_id": None # 缺失照片！
        }]
    }
    with pytest.raises(BusinessException) as exc:
        InspectionAtomicService.submit_inspection(db_session, admin.id, payload)
    assert exc.value.code == 30002

def test_inspection_tx_success_and_fault_interlock(db_session):
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    admin = db_session.query(User).filter(User.username == "admin").first()
    eq = Equipment(
        equipment_code="DEV-INSP-OK-001",
        equipment_name="循环泵电机",
        equipment_type="MOTOR",
        work_type="ELECTRICAL",
        location_id=loc.id,
        model_spec="Y2-132M",
        status="RUNNING"
    )
    db_session.add(eq)
    db_session.commit()

    # 创建一个模拟凭证文件
    file_record = EquipmentFile(
        file_tag="FAULT_IMG",
        original_filename="motor_hot.jpg",
        storage_path="/uploads/motor_hot.jpg",
        file_size_bytes=1024,
        mime_type="image/jpeg",
        file_sha256="abc12345",
        is_linked=False
    )
    db_session.add(file_record)
    db_session.commit()

    # 提交带照片的异常打卡
    payload = {
        "equipment_id": eq.id,
        "details": [{
            "plan_item_id": 1,
            "check_item_name": "绕组温升",
            "is_normal": False,
            "anomaly_desc": "温度高达95℃，冒青烟",
            "evidence_file_id": file_record.id
        }]
    }
    res = InspectionAtomicService.submit_inspection(db_session, admin.id, payload)
    assert res["has_anomaly"] is True
    assert res["interlocked_fault_id"] is not None

    # 验证设备状态跃迁为 FAULTY
    db_session.refresh(eq)
    assert eq.status == "FAULTY"

    # 验证自动联锁生成的故障单
    fault = db_session.query(FaultRecord).filter(FaultRecord.id == res["interlocked_fault_id"]).first()
    assert fault is not None
    assert fault.source_type == "INSPECTION_AUTO"
    assert fault.status == "OPEN"
    assert "绕组温升" in fault.fault_title

def test_fault_claim_optimistic_locking(db_session):
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    admin = db_session.query(User).filter(User.username == "admin").first()
    eng2 = User(username="eng2", full_name="张工", role_code="ENGINEER", work_type="GENERAL", employee_no="EMP-02", email="eng2@t.com", password_hash="hash")
    db_session.add(eng2)
    
    fault = FaultRecord(
        fault_code="FLT-CLAIM-TEST-001",
        source_type="MANUAL_REPORT",
        equipment_id=1,
        snapshot_location_id=loc.id,
        fault_title="风机轴承破裂",
        fault_desc="轴承破裂卡死",
        fault_system="MECHANICAL",
        fault_part="轴承箱",
        severity_level="CRITICAL",
        status="OPEN",
        reported_by=admin.id
    )
    db_session.add(fault)
    db_session.commit()

    # 工程师1认领成功
    res1 = FaultClaimService.claim_fault(db_session, fault.id, admin.id)
    assert res1["status"] == "IN_PROGRESS"

    # 工程师2同时认领 -> 应当触发 40003 抢单冲突
    with pytest.raises(BusinessException) as exc:
        FaultClaimService.claim_fault(db_session, fault.id, eng2.id)
    assert exc.value.code == 40003
    assert "已由" in exc.value.message or "认领" in exc.value.message

def test_recommendation_engine(db_session):
    # 写入一条知识库条目
    article = KnowledgeArticle(
        article_code="KB-TEST-001",
        equipment_type="FAN",
        equipment_model="CF-500",
        fault_system="MECHANICAL",
        fault_title="离心风机异响与轴承温升高",
        fault_phenomenon="风机运行时伴有剧烈金属摩擦异响，轴承外壳温升至85度",
        root_cause="轴承长期未注油，内部滚珠干磨剥落",
        solution_steps="更换SKF 6205轴承，加注美孚高温润滑脂",
        is_featured=True
    )
    db_session.add(article)
    db_session.commit()

    # 检索相似案例
    cases = RecommendationEngine.get_similar_cases(
        db_session,
        equipment_type="FAN",
        model_spec="CF-500",
        fault_desc="离心风机 轴承 异响"
    )
    assert len(cases) >= 1
    assert cases[0]["title"] == "离心风机异响与轴承温升高"
    assert cases[0]["match_score"] >= 60.0
    assert "SKF 6205" in cases[0]["solution_steps"]

def test_excel_processor():
    headers = ["设备编码", "设备名称", "状态"]
    rows = [["DEV-001", "电机A", "正常"], ["DEV-002", "风机B", "待维护"]]
    excel_bytes = ExcelProcessor.export_to_excel(headers, rows)
    assert len(excel_bytes) > 0

    parsed = ExcelProcessor.parse_excel(excel_bytes)
    assert len(parsed) == 2
    assert parsed[0]["设备编码"] == "DEV-001"
    assert parsed[1]["设备名称"] == "风机B"
