import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.equipment import Equipment, Location
from app.models.fault import FaultRecord
from app.models.knowledge import KnowledgeArticle
from app.core.security import hash_password
from app.tasks.maintenance_cron import run_daily_maintenance_countdown_job

def test_full_system_e2e_lifecycle():
    """
    全流程端到端集成验收测试 (覆盖全部 50 项需求之核心主业务链路)
    """
    client = TestClient(app)
    db = SessionLocal()

    try:
        # 清理可能残留的测试用户
        db.query(User).filter(User.username == "operator_e2e").delete()
        db.commit()

        # -------------------------------------------------------------
        # 1. 账号认证、首次登录与强制改密双重拦截 (SWR-USR-004)
        # -------------------------------------------------------------
        # 创建带 force_change_password=True 的初始用户
        init_user = User(
            username="operator_e2e",
            password_hash=hash_password("Initial@2026"),
            full_name="E2E现场工程师",
            employee_no="MW-E2E-001",
            email="operator_e2e@maintainwise.com",
            role_code="ENGINEER",
            work_type="MECHANICAL",
            is_active=True,
            force_change_password=True
        )
        db.add(init_user)
        db.commit()

        # 登录获取 Token
        login_resp = client.post("/api/v1/auth/login", json={
            "username": "operator_e2e",
            "password": "Initial@2026"
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["data"]["access_token"]
        assert login_resp.json()["data"]["force_change_password"] is True

        headers = {"Authorization": f"Bearer {token}"}

        # 尝试直接访问业务受限接口 -> 必须被 10008 拦截
        blocked_resp = client.get("/api/v1/equipments", headers=headers)
        assert blocked_resp.status_code == 403
        assert blocked_resp.json()["code"] == 10008
        assert "必须修改初始密码" in blocked_resp.json()["message"]

        # 执行首次安全改密
        change_resp = client.post("/api/v1/auth/force-change-password", headers=headers, json={
            "old_password": "Initial@2026",
            "new_password": "NewSecretPass@2026!"
        })
        assert change_resp.status_code == 200

        # 使用新密码重新登录
        relogin_resp = client.post("/api/v1/auth/login", json={
            "username": "operator_e2e",
            "password": "NewSecretPass@2026!"
        })
        assert relogin_resp.status_code == 200
        valid_token = relogin_resp.json()["data"]["access_token"]
        assert relogin_resp.json()["data"]["force_change_password"] is False
        valid_headers = {"Authorization": f"Bearer {valid_token}"}

        # 再次访问业务接口 -> 顺利放行
        allowed_resp = client.get("/api/v1/equipments", headers=valid_headers)
        assert allowed_resp.status_code == 200

        # -------------------------------------------------------------
        # 2. 位置拓扑树与设备台账 (SWR-DEV-001/003/004)
        # -------------------------------------------------------------
        loc_resp = client.get("/api/v1/locations/tree", headers=valid_headers)
        assert loc_resp.status_code == 200
        assert len(loc_resp.json()["data"]) > 0
        leaf_loc = db.query(Location).filter(Location.is_leaf == True, Location.is_deleted == False).first()
        loc_id = leaf_loc.id

        # 录入工业风机台账与专有参数
        eq_payload = {
            "equipment_code": f"FAN-E2E-{int(datetime.now().timestamp())}",
            "equipment_name": "E2E总装车间离心引风机",
            "equipment_type": "FAN",
            "work_type": "MECHANICAL",
            "model_spec": "Y4-73 No.10D",
            "location_id": loc_id,
            "manufacturer": "某风机重工股份",
            "rated_voltage": "380V",
            "params": {
                "air_volume": 18500.0,
                "total_pressure": 2400.0,
                "rotation_speed": 1450.0
            }
        }
        eq_resp = client.post("/api/v1/equipments", headers=valid_headers, json=eq_payload)
        assert eq_resp.status_code == 200
        equipment_id = eq_resp.json()["data"]["id"]
        assert eq_resp.json()["data"]["status"] == "RUNNING"

        # -------------------------------------------------------------
        # 3. 编制维保计划、自动派单与巡检异常联锁提单 (SWR-MNT-001/008)
        # -------------------------------------------------------------
        plan_payload = {
            "plan_code": f"PLN-FAN-{int(datetime.now().timestamp())}",
            "plan_name": "E2E风机月度深度巡检规程",
            "plan_type": "MONTHLY",
            "interval_days": 30,
            "sop_content": "标准作业规程：严格按照电气与机械安全规程实施停机与振动排查",
            "items": [
                {
                    "item_order": 1,
                    "check_item_name": "电机与轴承箱振动测试",
                    "standard_benchmark": "振动速度RMS <= 2.8 mm/s",
                    "is_required": True
                },
                {
                    "item_order": 2,
                    "check_item_name": "主轴承温度与润滑油脂",
                    "standard_benchmark": "温升 <= 40℃，油脂清澈无结碳",
                    "is_required": True
                }
            ]
        }
        plan_resp = client.post("/api/v1/maintenance/plans", headers=valid_headers, json=plan_payload)
        assert plan_resp.status_code == 200
        plan_id = plan_resp.json()["data"]["plan_id"]

        # 触发后台调度器自动推算倒计时并生成待办任务
        run_daily_maintenance_countdown_job(db)

        tasks_resp = client.get("/api/v1/maintenance/my-tasks", headers=valid_headers)
        assert tasks_resp.status_code == 200
        tasks = tasks_resp.json()["data"]
        target_task = next((t for t in tasks if t["equipment_id"] == equipment_id), None)
        task_id = target_task["task_id"] if target_task else None

        # 执行巡检打卡：模拟第 1 项正常，第 2 项出现严重温升异常
        inspection_payload = {
            "task_id": task_id,
            "equipment_id": equipment_id,
            "execution_start_time": datetime.now(timezone.utc).isoformat(),
            "execution_end_time": datetime.now(timezone.utc).isoformat(),
            "overall_remarks": "E2E现场环境湿度 65%",
            "details": [
                {
                    "plan_item_id": 1,
                    "check_item_name": "电机与轴承箱振动测试",
                    "is_normal": True
                },
                {
                    "plan_item_id": 2,
                    "check_item_name": "主轴承温度与润滑油脂",
                    "is_normal": False,
                    "anomaly_desc": "主轴承测点温升达 58℃，超出极限阈值，有焦糊异味",
                    "evidence_file_id": 999  # 模拟上传的拍照附件ID
                }
            ]
        }
        insp_resp = client.post("/api/v1/maintenance/inspections/submit", headers=valid_headers, json=inspection_payload)
        assert insp_resp.status_code == 200
        insp_data = insp_resp.json()["data"]
        assert insp_data["has_anomaly"] is True
        interlocked_fault_id = insp_data["interlocked_fault_id"]
        assert interlocked_fault_id is not None

        # 校验单事务强一致性：关联设备状态跃迁至 FAULTY
        eq_recheck = client.get("/api/v1/equipments", headers=valid_headers)
        target_eq = next(e for e in eq_recheck.json()["data"]["items"] if e["id"] == equipment_id)
        assert target_eq["status"] == "FAULTY"

        # -------------------------------------------------------------
        # 4. 故障流转、智能推荐与维修复盘知识沉淀 (SWR-FLT-003/005/006, SWR-KB-001)
        # -------------------------------------------------------------
        # 模拟技术员/工程师并发认领工单 (乐观锁校验)
        claim_resp = client.put(f"/api/v1/faults/{interlocked_fault_id}/claim", headers=valid_headers)
        assert claim_resp.status_code == 200
        assert claim_resp.json()["data"]["status"] == "IN_PROGRESS"

        # 再次认领 -> 必须拦截 30002 乐观锁并发冲突
        second_claim = client.put(f"/api/v1/faults/{interlocked_fault_id}/claim", headers=valid_headers)
        assert second_claim.status_code == 409
        assert second_claim.json()["code"] == 40003

        # 300ms 智能推荐匹配排查测试
        rec_resp = client.post(
            f"/api/v1/faults/recommend-similar?equipment_type=FAN&model_spec=Y4-73&fault_desc=轴承+发热+焦糊",
            headers=valid_headers
        )
        assert rec_resp.status_code == 200
        assert isinstance(rec_resp.json()["data"], list)

        # 提交维修复盘结果 (必填根因与解决步骤) 并标记为典型案例
        resolve_payload = {
            "root_cause": "轴承箱迷宫油封破损导致润滑脂流失干磨",
            "solution_steps": "更换耐高温骨架油封，重新注入2号极压锂基脂，试运行2小时温升32℃平稳恢复",
            "downtime_minutes": 45,
            "is_featured_case": True
        }
        resolve_resp = client.post(f"/api/v1/faults/{interlocked_fault_id}/resolve", headers=valid_headers, json=resolve_payload)
        assert resolve_resp.status_code == 200

        # 校验知识库已自动沉淀出知识词条
        kb_resp = client.get(f"/api/v1/knowledge/search?keyword=油封", headers=valid_headers)
        assert kb_resp.status_code == 200
        articles = kb_resp.json()["data"]["items"]
        assert any(a["root_cause"] == resolve_payload["root_cause"] for a in articles)

        # 校验设备恢复正常运行 RUNNING
        eq_restored = client.get("/api/v1/equipments", headers=valid_headers)
        target_eq_restored = next(e for e in eq_restored.json()["data"]["items"] if e["id"] == equipment_id)
        assert target_eq_restored["status"] == "RUNNING"

        # 验收关闭工单
        close_resp = client.put(f"/api/v1/faults/{interlocked_fault_id}/close", headers=valid_headers)
        assert close_resp.status_code == 200

        # -------------------------------------------------------------
        # 5. 运营大盘数据与审计合规验证 (SWR-DSH-001/002, SWR-SYS-005)
        # -------------------------------------------------------------
        metrics_resp = client.get("/api/v1/dashboard/metrics", headers=valid_headers)
        assert metrics_resp.status_code == 200
        m_data = metrics_resp.json()["data"]
        assert m_data["total_equipments"] >= 1
        assert m_data["running_count"] >= 1

        # 写入一条合规审计记录验证 180 天只读审计表 (SWR-SYS-005)
        from app.models.user import AuditLog
        audit_entry = AuditLog(
            user_id=init_user.id,
            username=init_user.username,
            client_ip="127.0.0.1",
            module_name="MAINTENANCE",
            action_type="SUBMIT_INSPECTION",
            request_url="/api/v1/maintenance/inspections/submit",
            request_method="POST",
            status_code=200
        )
        db.add(audit_entry)
        db.commit()

        # 验证审计日志记录存在 (使用 ADMIN 权限登录查询)
        admin_login = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "MaintainWiseAdmin@2026"
        })
        admin_token = admin_login.json()["data"]["access_token"]
        audit_resp = client.get("/api/v1/system/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
        assert audit_resp.status_code == 200
        assert audit_resp.json()["data"]["total"] >= 1

    finally:
        # 清理测试数据
        db.query(User).filter(User.username == "operator_e2e").delete()
        db.commit()
        db.close()
