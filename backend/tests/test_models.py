import pytest
from app.models.user import User
from app.models.equipment import Location, Equipment, EquipmentParam

def test_admin_user_seeded(db_session):
    user = db_session.query(User).filter(User.username == "admin").first()
    assert user is not None
    assert user.role_code == "ADMIN"
    assert user.work_type == "GENERAL"
    assert user.force_change_password is True
    assert user.is_active is True
    assert user.is_deleted is False

def test_location_tree_seeded(db_session):
    locs = db_session.query(Location).filter(Location.is_deleted == False).all()
    assert len(locs) >= 4
    leaf = db_session.query(Location).filter(Location.location_code == "LOC-STN-A1").first()
    assert leaf is not None
    assert leaf.is_leaf is True
    assert leaf.level_depth == 4

def test_equipment_creation(db_session):
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    eq = Equipment(
        equipment_code="DEV-PLC-TEST-002",
        equipment_name="主控PLC测试机",
        equipment_type="PLC",
        work_type="AUTOMATION",
        location_id=loc.id,
        model_spec="Siemens S7-1200 CPU 1214C",
        maintenance_interval_days=30,
        status="RUNNING"
    )
    db_session.add(eq)
    db_session.commit()
    
    # 关联专有参数
    param = EquipmentParam(
        equipment_id=eq.id,
        ip_address="192.168.1.10",
        comm_protocol="PROFINET",
        io_points_spec="14DI/10DO/2AI",
        extra_params={"rack": 0, "slot": 1}
    )
    db_session.add(param)
    db_session.commit()

    queried = db_session.query(Equipment).filter(Equipment.equipment_code == "DEV-PLC-TEST-002").first()
    assert queried is not None
    assert queried.status == "RUNNING"
    assert queried.equipment_type == "PLC"

    param_queried = db_session.query(EquipmentParam).filter(EquipmentParam.equipment_id == eq.id).first()
    assert param_queried.ip_address == "192.168.1.10"
    assert param_queried.extra_params["rack"] == 0

from app.repositories.base import apply_work_type_scope

def test_work_type_data_scope_filtering(db_session):
    loc = db_session.query(Location).filter(Location.is_leaf == True).first()
    
    # 创建一台机械风机设备
    fan = Equipment(
        equipment_code="DEV-FAN-SCOPE-001",
        equipment_name="离心风机",
        equipment_type="FAN",
        work_type="MECHANICAL",
        location_id=loc.id,
        model_spec="CF-500",
        status="RUNNING"
    )
    db_session.add(fan)
    db_session.commit()

    # 模拟电气工程师
    elec_user = User(username="elec_eng", role_code="ENGINEER", work_type="ELECTRICAL", employee_no="EMP-E01", email="e@test.com", password_hash="hash")
    # 模拟机械工程师
    mech_user = User(username="mech_eng", role_code="ENGINEER", work_type="MECHANICAL", employee_no="EMP-M01", email="m@test.com", password_hash="hash")
    # 模拟管理员
    admin_user = User(username="adm", role_code="ADMIN", work_type="GENERAL", employee_no="EMP-A01", email="a@test.com", password_hash="hash")

    # 电气工程师过滤查询
    q_elec = apply_work_type_scope(db_session.query(Equipment).filter(Equipment.is_deleted == False), Equipment, elec_user)
    results_elec = [e.equipment_code for e in q_elec.all()]
    assert "DEV-FAN-SCOPE-001" not in results_elec

    # 机械工程师过滤查询
    q_mech = apply_work_type_scope(db_session.query(Equipment).filter(Equipment.is_deleted == False), Equipment, mech_user)
    results_mech = [e.equipment_code for e in q_mech.all()]
    assert "DEV-FAN-SCOPE-001" in results_mech

    # 管理员过滤查询
    q_admin = apply_work_type_scope(db_session.query(Equipment).filter(Equipment.is_deleted == False), Equipment, admin_user)
    results_admin = [e.equipment_code for e in q_admin.all()]
    assert "DEV-FAN-SCOPE-001" in results_admin
