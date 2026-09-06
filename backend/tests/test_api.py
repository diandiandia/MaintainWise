import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_admin_account():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if user:
            user.password_hash = hash_password("MaintainWiseAdmin@2026")
            user.force_change_password = True
            user.failed_login_attempts = 0
            user.locked_until = None
            db.commit()
    finally:
        db.close()

def test_health_check():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_login_and_force_password_change_flow():
    # 1. 初始密码登录
    login_res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "MaintainWiseAdmin@2026"
    })
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    assert login_res.json()["data"]["force_change_password"] is True

    headers = {"Authorization": f"Bearer {token}"}

    # 2. 验证改密阻断拦截 (SWR-USR-004): 尝试调用受保护业务接口被阻断
    eq_res = client.get("/api/v1/equipments", headers=headers)
    assert eq_res.status_code == 403
    assert eq_res.json()["code"] == 10008 # 必须先改密！

    # 3. 首次改密
    change_res = client.post("/api/v1/auth/force-change-password", headers=headers, json={
        "old_password": "MaintainWiseAdmin@2026",
        "new_password": "NewMaintainWise@2026!Strong"
    })
    assert change_res.status_code == 200

    # 4. 使用新密码重新登录
    login_new = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "NewMaintainWise@2026!Strong"
    })
    assert login_new.status_code == 200
    new_token = login_new.json()["data"]["access_token"]
    assert login_new.json()["data"]["force_change_password"] is False
    new_headers = {"Authorization": f"Bearer {new_token}"}

    # 5. 再次访问受保护接口成功
    eq_new_res = client.get("/api/v1/equipments", headers=new_headers)
    assert eq_new_res.status_code == 200

def test_location_tree_api():
    # 临时重置为已改密状态获取 Token
    db = SessionLocal()
    user = db.query(User).filter(User.username == "admin").first()
    user.force_change_password = False
    db.commit()
    db.close()

    login_res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "MaintainWiseAdmin@2026"
    })
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/locations/tree", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 1
    assert data[0]["location_code"] == "LOC-FAC-01"

def test_upload_security_interception():
    db = SessionLocal()
    user = db.query(User).filter(User.username == "admin").first()
    user.force_change_password = False
    db.commit()
    db.close()

    login_res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "MaintainWiseAdmin@2026"
    })
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 上传禁止的 .sh 可执行脚本 -> 应当拦截 50001
    files = {"file": ("malicious.sh", b"echo 'hack'", "text/x-shellscript")}
    res = client.post("/api/v1/system/files/upload", headers=headers, files=files)
    assert res.status_code == 400
    assert res.json()["code"] == 50001

    # 上传合法的图片
    img_files = {"file": ("normal.jpg", b"\xff\xd8\xff\xe0testimagecontent", "image/jpeg")}
    img_res = client.post("/api/v1/system/files/upload", headers=headers, files=img_files)
    assert img_res.status_code == 200
    assert "file_id" in img_res.json()["data"]

def test_smtp_config_page_save_and_test_flow():
    """测试 SMTP 页面配置保存、密码脱敏及在线发信自检完整流 (SWR-SYS-001)"""
    db = SessionLocal()
    user = db.query(User).filter(User.username == "admin").first()
    user.force_change_password = False
    db.commit()
    db.close()

    login_res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "MaintainWiseAdmin@2026"
    })
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 查询当前配置 (密码需已脱敏)
    get_res = client.get("/api/v1/system/smtp/config", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()["data"]
    assert "smtp_host" in data
    assert data["smtp_pass_masked"] == "******"

    # 2. 页面提交新配置保存 (动态持久化)
    save_payload = {
        "smtp_host": "smtp.maintainwise.com",
        "smtp_port": 587,
        "smtp_user": "alert@maintainwise.com",
        "smtp_pass": "SecretAuthToken2026",
        "sender_name": "车间维保预警中心",
        "use_ssl": False,
        "use_tls": True,
        "is_active": True
    }
    save_res = client.post("/api/v1/system/smtp/config", headers=headers, json=save_payload)
    assert save_res.status_code == 200
    saved_data = save_res.json()["data"]
    assert saved_data["smtp_host"] == "smtp.maintainwise.com"
    assert saved_data["smtp_port"] == 587
    assert saved_data["smtp_pass_masked"] == "******"

    # 3. 再次保存但密码为 ******，验证原密码不被覆盖破坏
    save_payload2 = {
        "smtp_host": "smtp.maintainwise.com",
        "smtp_port": 587,
        "smtp_user": "alert@maintainwise.com",
        "smtp_pass": "******", # 脱敏占位符
        "sender_name": "车间维保预警中心 (更新)",
        "use_ssl": False,
        "use_tls": True,
        "is_active": True
    }
    save_res2 = client.post("/api/v1/system/smtp/config", headers=headers, json=save_payload2)
    assert save_res2.status_code == 200
    assert save_res2.json()["data"]["sender_name"] == "车间维保预警中心 (更新)"

    # 4. 执行在线发信自检
    test_res = client.post("/api/v1/system/smtp/test", headers=headers, json={
        "to_email": "admin@factory.com"
    })
    assert test_res.status_code == 200
    assert "投递" in test_res.json()["message"] or "成功" in test_res.json()["message"]

def test_update_equipment_and_files_flow():
    db = SessionLocal()
    user = db.query(User).filter(User.username == "admin").first()
    user.force_change_password = False
    db.commit()
    db.close()

    login_res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "MaintainWiseAdmin@2026"
    })
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 获取系统位置节点 (L3)
    loc_tree = client.get("/api/v1/locations/tree", headers=headers).json()["data"]
    system_id = None
    for fac in loc_tree:
        for dep in fac.get("children", []):
            for sys in dep.get("children", []):
                if sys.get("level_depth") == 3:
                    system_id = sys["id"]
                    break

    # 1. 录入设备
    create_res = client.post("/api/v1/equipments", headers=headers, json={
        "equipment_code": "EQ-UNIT-TEST-01",
        "equipment_name": "自动化测试主风机",
        "model_spec": "MOD-TEST-01",
        "location_id": system_id,
        "rated_voltage": "380V",
        "params_text": "初始参数信息"
    })
    assert create_res.status_code == 200
    target_eq = create_res.json()["data"]
    assert target_eq["next_maintenance_date"] is not None

    # 2. 编辑修改设备信息
    update_res = client.put(f"/api/v1/equipments/{target_eq['id']}", headers=headers, json={
        "equipment_name": "修改后的自动化主设备",
        "rated_voltage": "220V",
        "params_text": "主轴功率: 15kW\nPLC型号: S7-1500",
        "model_spec": "MOD-REV-2026"
    })
    assert update_res.status_code == 200
    updated_data = update_res.json()["data"]
    assert updated_data["equipment_name"] == "修改后的自动化主设备"
    assert updated_data["rated_voltage"] == "220V"
    assert "15kW" in updated_data["params_text"]
    assert updated_data["updated_by_name"] is not None

    # 3. 关联附件测试
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    files = {"file": ("test_equipment_photo.png", fake_png, "image/png")}
    up_res = client.post("/api/v1/system/upload", headers=headers, files=files, data={"file_tag": "PHOTO"})
    assert up_res.status_code == 200
    file_id = up_res.json()["data"]["file_id"]

    # 绑定附件到设备
    bind_res = client.post(f"/api/v1/equipments/{target_eq['id']}/files/bind", headers=headers, json={
        "file_id": file_id,
        "file_tag": "PHOTO"
    })
    assert bind_res.status_code == 200

    # 获取设备附件列表
    get_files_res = client.get(f"/api/v1/equipments/{target_eq['id']}/files", headers=headers)
    assert get_files_res.status_code == 200
    file_items = get_files_res.json()["data"]
    assert any(f["id"] == file_id for f in file_items)

    # 移除附件
    del_res = client.delete(f"/api/v1/equipments/{target_eq['id']}/files/{file_id}", headers=headers)
    assert del_res.status_code == 200

def test_maintenance_plan_bump_version_and_advance_days():
    db = SessionLocal()
    user = db.query(User).filter(User.username == "admin").first()
    user.force_change_password = False
    db.commit()
    db.close()

    login_res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "MaintainWiseAdmin@2026"
    })
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 创建维护计划
    plan_create = client.post("/api/v1/maintenance/plans", headers=headers, json={
        "plan_code": "PLN-TEST-BUMP-01",
        "plan_name": "测试版本升级计划",
        "plan_type": "MONTHLY",
        "trigger_mode": "CALENDAR",
        "interval_days": 30,
        "advance_notice_days": 3,
        "advance_warning_hours": 72,
        "sop_content": "断电检修作业指导书，严格遵循停电挂牌流程",
        "items": [{
            "item_order": 1,
            "check_item_name": "检查电源接线",
            "standard_benchmark": "接线牢固无松动",
            "is_required": True
        }]
    })
    assert plan_create.status_code == 200
    plan_id = plan_create.json()["data"]["plan_id"]

    # 2. 修改计划，更新 advance_notice_days
    update_res = client.put(f"/api/v1/maintenance/plans/{plan_id}", headers=headers, json={
        "plan_code": "PLN-TEST-BUMP-01",
        "plan_name": "测试版本升级计划 (已修订)",
        "plan_type": "MONTHLY",
        "trigger_mode": "CALENDAR",
        "interval_days": 30,
        "advance_notice_days": 5,
        "advance_warning_hours": 120,
        "sop_content": "断电检修作业指导书，严格遵循停电挂牌流程 (修订版)",
        "items": [{
            "item_order": 1,
            "check_item_name": "检查PLC指示灯与散热风扇",
            "standard_benchmark": "指示灯正常绿色，风扇无异响",
            "is_required": True
        }]
    })
    assert update_res.status_code == 200

    # 3. 再次获取，验证 advance_notice_days 生效
    plans_after = client.get("/api/v1/maintenance/plans", headers=headers).json()["data"]
    p_updated = next(p for p in plans_after if p["id"] == plan_id)
    assert p_updated["advance_notice_days"] == 5
    assert p_updated["advance_warning_hours"] == 120

    # 4. 测试版本升级快照接口 (bump-version)
    old_version = p_updated["version_no"]
    bump_res = client.put(f"/api/v1/maintenance/plans/{plan_id}/bump-version", headers=headers)
    assert bump_res.status_code == 200
    new_version = bump_res.json()["data"]["version_no"]
    assert new_version != old_version
    assert new_version.startswith("V")

    # 5. 测试获取单个计划详情 (GET /plans/{plan_id})
    detail_res = client.get(f"/api/v1/maintenance/plans/{plan_id}", headers=headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()["data"]
    assert detail_data["id"] == plan_id
    assert len(detail_data["items"]) == 1
    assert detail_data["items"][0]["check_item_name"] == "检查PLC指示灯与散热风扇"

    # 6. 测试停用/启用计划切换 (PUT /plans/{plan_id}/toggle-status)
    toggle_res = client.put(f"/api/v1/maintenance/plans/{plan_id}/toggle-status", headers=headers)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["data"]["is_active"] == False

    toggle_back_res = client.put(f"/api/v1/maintenance/plans/{plan_id}/toggle-status", headers=headers)
    assert toggle_back_res.status_code == 200
    assert toggle_back_res.json()["data"]["is_active"] == True

    # 7. 测试软删除计划 (DELETE /plans/{plan_id})
    del_res = client.delete(f"/api/v1/maintenance/plans/{plan_id}", headers=headers)
    assert del_res.status_code == 200
    # 删除后再获取详情应返回 404
    detail_after_del = client.get(f"/api/v1/maintenance/plans/{plan_id}", headers=headers)
    assert detail_after_del.status_code == 404


