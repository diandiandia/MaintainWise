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
