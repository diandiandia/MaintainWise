# MaintainWise — 软件详细设计说明书 (SDD)
## (Software Detailed Design Specification)

> **文档版本**：V1.0  
> **编制日期**：2026-09-05  
> **标准遵循**：GB/T 8567-2006 软件详细设计规格规范  
> **关联依据**：  
> - 软件需求规格：[software_requirements_specification.md](file:///root/MaintainWise/docs/software_requirements_specification.md)  
> - 软件反省报告：[software_requirements_reflection.md](file:///root/MaintainWise/docs/software_requirements_reflection.md)

---

## 目录
1. [软件分层架构与工程目录结构](#1-软件分层架构与工程目录结构)
2. [全局统一工业业务错误码字典 (Error Code Dictionary)](#2-全局统一工业业务错误码字典-error-code-dictionary)
3. [核心服务类与并发控制设计 (Service Layer & Concurrency)](#3-核心服务类与并发控制设计-service-layer--concurrency)
4. [设备参数自由文本建模与灵活扩展设计 (取代死板11类Schema强校验)](#4-设备参数自由文本建模与灵活扩展设计-取代死板11类schema强校验)
5. [后台守护调度任务设计 (Background Workers)](#5-后台守护调度任务设计-background-workers)
6. [前端工程、状态流转与触控视图组件设计](#6-前端工程状态流转与触控视图组件设计)
7. [软件设计追踪矩阵 (SWR to SDD Traceability)](#7-软件设计追踪矩阵-swr-to-sdd-traceability)

---

## 1. 软件分层架构与工程目录结构

系统遵循现代整洁分层架构（Clean Architecture / Layered Architecture），将表现层、业务控制层、领域服务层、持久层及基础设施层解耦：

```
/root/MaintainWise/
├── backend/                        # 后端服务工程 (Python 3.12+ / FastAPI / SQLAlchemy 2.0)
│   ├── app/
│   │   ├── api/                    # 控制器/路由层 (Routers)
│   │   │   ├── v1/
│   │   │   │   ├── auth.py         # 认证、登录、改密、Token刷新
│   │   │   │   ├── users.py        # 用户管理 CRUD (不设车间主管，免责任工种隔离)
│   │   │   │   ├── locations.py    # 4级层级拓扑树 API (工厂/部门/系统/设备)
│   │   │   │   ├── equipments.py   # 设备信息、参数、履历与导入导出
│   │   │   │   ├── maintenance.py  # 设备维护计划(最小单位小时)、工单接单编辑与图片凭证、现场维护单提交
│   │   │   │   ├── faults.py       # 故障报修、接单乐观锁、复盘关闭
│   │   │   │   ├── knowledge.py    # 知识库全文检索、智能推荐打分
│   │   │   │   ├── training.py     # 培训课程、挂接案例、实训考核
│   │   │   │   ├── dashboard.py    # FCM设备运维管理平台(数据平台)卡片、角色工作台待办
│   │   │   │   └── system.py       # SMTP测试、通知配置、审计日志
│   │   │   └── deps.py             # 依赖注入 (get_db, get_current_user, require_role)
│   │   ├── core/                   # 核心基础设施
│   │   │   ├── config.py           # Pydantic BaseSettings 环境配置读取
│   │   │   ├── database.py         # 异步连接池与 SessionLocal 工厂
│   │   │   ├── security.py         # bcrypt 密码加盐、JWT 生成与验证
│   │   │   ├── redis.py            # Redis 连接池与分布式锁封装
│   │   │   ├── exceptions.py       # 业务异常基类与全局统一异常处理器
│   │   │   └── audit.py            # 180天审计日志切面 (JSON Diff 算法)
│   │   ├── models/                 # SQLAlchemy 2.0 ORM 数据模型
│   │   │   ├── base.py             # 审计基类 (id, created_at, updated_at, is_deleted)
│   │   │   ├── user.py             # User, Role, AuditLog
│   │   │   ├── equipment.py        # Location, Equipment, EquipmentParam, EquipmentFile
│   │   │   ├── maintenance.py      # Plan, PlanItem, Task, InspectionRecord, Detail
│   │   │   ├── fault.py            # FaultRecord, SparePart
│   │   │   ├── knowledge.py        # KnowledgeArticle
│   │   │   └── training.py         # Course, CourseCase, TrainingRecord, UserScore
│   │   ├── schemas/                # Pydantic 强类型请求/响应 DTO
│   │   │   ├── equipment_params.py # 11类设备专有参数强校验 Schema
│   │   │   ├── inspection.py       # 现场维护单原子提交与证据 Payload Schema
│   │   │   ├── fault.py            # 故障录入与复盘 Schema
│   │   │   └── common.py           # 分页响应包与标准结果返回封包
│   │   ├── services/               # 领域业务服务层
│   │   │   ├── state_machine.py    # 设备与故障有限状态机服务
│   │   │   ├── inspection_tx.py    # 现场维护异常联锁单事务提单服务
│   │   │   ├── fault_claim.py      # 故障接单乐观并发控制服务
│   │   │   ├── recommend_engine.py # 双阶段故障智能推荐打分引擎
│   │   │   └── excel_processor.py  # 流式 Excel 导入导出解析器
│   │   └── tasks/                  # 异步守护与定时调度任务 (APScheduler / Celery)
│   │       ├── maintenance_cron.py # 维护倒计时小时级游标分块扫描与派单
│   │       ├── email_dispatcher.py # 邮件防重调度投递
│   │       ├── sla_monitor.py      # SLA 超时监控轮询
│   │       └── file_cleaner.py     # 24小时未关联孤儿文件清理任务
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                       # 前端交互工程 (Vue 3 / Vite / TypeScript / Element Plus)
│   ├── src/
│   │   ├── api/                    # Axios API 请求封装与全局拦截器
│   │   ├── components/             # 通用业务组件 (图片比对浮窗、时间线、参数渲染器、快捷悬浮菜单)
│   │   ├── directives/             # 权限控制指令 (v-permission 按钮与DOM节点物理移除)
│   │   ├── router/                 # Vue Router 路由定义与强制改密/RBAC守卫 (Route Guard)
│   │   ├── stores/                 # Pinia 状态管理 (Auth, Todo, Equipment, Inspection)
│   │   ├── views/                  # 业务页面 (数据平台FCM、现场维护单、设备信息、故障复盘、用户管理、系统配置)
│   │   └── styles/                 # 工业触控适配 CSS (48px 触控热区)
│   ├── Dockerfile
│   └── package.json
└── deploy/                         # 容器化与运维脚本 (Nginx, Postgres, deploy_linux.sh)
```

---

## 2. 全局统一工业业务错误码字典 (Error Code Dictionary)

为了让工业现场技术人员、工程师与工控终端明确获知异常根因，系统废除晦涩的无状态报错，建立 5 位标准业务错误代码：

```json
{
  "code": 30002,
  "message": "检查项【电机轴承润滑】判定为异常，必须上传现场照片证据",
  "data": null,
  "timestamp": 1725514800
}
```

| 错误代码 (Code) | HTTP Status | 业务标识符 (Identifier) | 错误提示说明与发生场景 |
|:---|:---:|:---|:---|
| **10001** | 403 | `ACCOUNT_LOCKED` | 连续 5 次密码错误，账户已被安全锁定 15 分钟 |
| **10002** | 403 | `ACCOUNT_DISABLED` | 账户已被管理员软禁用，无法登录系统 |
| **10003** | 403 | `PERMISSION_DENIED` | 越权访问：当前角色或专业工作类型无权执行该动作 |
| **10004** | 401 | `TOKEN_EXPIRED` | 登录会话已超过 30 分钟无操作，请重新登录 |
| **10005** | 400 | `INVALID_CREDENTIALS` | 用户名或密码错误 |
| **10008** | 403 | `FORCE_PASSWORD_CHANGE_REQUIRED` | 首次登录或密码过期，必须修改初始密码方可继续使用 |
| **20001** | 400 | `CANNOT_DELETE_NODE_WITH_CHILDREN` | 目标位置节点存在子节点或下挂设备信息，禁止删除 |
| **20002** | 400 | `EQUIPMENT_CODE_DUPLICATE` | 设备编码已存在，请更换唯一编码 |
| **20003** | 400 | `CYCLIC_HIERARCHY_DETECTED` | 拓扑位置修改失败：检测到循环依赖成环路径 |
| **20004** | 400 | `MAX_DEPTH_EXCEEDED` | 位置层级深度超出限制，系统固定支持 3 级（工厂/部门/系统）并在系统下挂载设备信息 |
| **20005** | 400 | `INVALID_STATUS_TRANSITION` | 设备生命周期状态跃迁非法（如报废设备不可恢复为正常） |
| **20006** | 400 | `EQUIPMENT_PARAM_INVALID` | 设备专有参数校验不合法（如 IP 格式错误或风量为负数） |
| **30001** | 400 | `INSPECTION_ITEM_MISSING` | 现场维护单提交失败：存在未评定的设备维护内容项 |
| **30002** | 400 | `INSPECTION_ANOMALY_PHOTO_REQUIRED` | 设备维护内容判定为异常时，必须强制上传现场照片证据 |
| **30003** | 400 | `PLAN_VERSION_CONFLICT` | 维护计划版本冲突，当前计划正在被其他工程师修改 |
| **30004** | 400 | `WORK_PROOF_REQUIRED` | 技术员提交现场维护单必须上传现场工作完成证据图片 |
| **40001** | 404 | `FAULT_NOT_FOUND` | 目标故障工单不存在或已被软删除 |
| **40002** | 400 | `INVALID_FAULT_STATE_TRANSITION` | 故障状态流转非法 |
| **40003** | 409 | `FAULT_ALREADY_CLAIMED` | **并发接单冲突**：该故障工单已被其他工程师抢先认领 |
| **40006** | 400 | `ROOT_CAUSE_REQUIRED` | 故障解决闭环必须填报根本原因与详细处理步骤 |
| **50001** | 400 | `EXECUTABLE_FILE_FORBIDDEN` | 文件上传安全拦截：严禁上传可执行脚本或程序 |
| **50002** | 413 | `FILE_SIZE_EXCEEDED` | 上传文件超出限制：图片不得超过 10MB，文档不得超过 50MB |
| **50003** | 500 | `SMTP_CONNECTION_FAILED` | SMTP 邮件服务器通信失败，请检查主机、端口与授权码 |

---

## 3. 核心服务类与并发控制设计 (Service Layer & Concurrency)

### 3.1 巡检异常单事务联锁提单服务 (`InspectionAtomicService`)
落实第一次反省与需求 `SWR-MNT-008`：技术员提交包含异常项的巡检表单时，采用单数据库事务完成全链路原子持久化。

```python
# backend/app/services/inspection_tx.py
from sqlalchemy.orm import Session
from app.models.maintenance import InspectionRecord, InspectionRecordDetail, MaintenanceTask
from app.models.fault import FaultRecord
from app.models.equipment import Equipment
from app.core.exceptions import BusinessException

class InspectionAtomicService:
    @staticmethod
    def submit_inspection(db: Session, user_id: int, payload: dict) -> dict:
        """
        单事务原子提交：
        1. 写入巡检主表与明细
        2. 异常自动联锁生成故障单并回填
        3. 跃迁设备状态
        4. 推算下次维护时间
        """
        task_id = payload.get("task_id")
        equipment_id = payload["equipment_id"]
        details_data = payload["details"] # List[CheckItemResult]
        
        # 1. 锁查询当前设备
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id, 
            Equipment.is_deleted == False
        ).with_for_update().first()
        
        if not equipment:
            raise BusinessException(code=20005, message="目标设备不存在或已被删除")
            
        has_anomaly = any(item["is_normal"] is False for item in details_data)
        
        # 2. 写入巡检主表
        inspection = InspectionRecord(
            task_id=task_id,
            equipment_id=equipment_id,
            snapshot_location_id=equipment.location_id, # 固化工位快照
            inspector_id=user_id,
            has_anomaly=has_anomaly,
            execution_start_time=payload["execution_start_time"],
            overall_remarks=payload.get("overall_remarks")
        )
        db.add(inspection)
        db.flush() # 获取 inspection.id
        
        generated_fault_id = None
        
        # 3. 批量处理打卡明细
        for item in details_data:
            detail = InspectionRecordDetail(
                record_id=inspection.id,
                plan_item_id=item["plan_item_id"],
                check_item_name_snapshot=item["check_item_name"],
                is_normal=item["is_normal"],
                anomaly_desc=item.get("anomaly_desc"),
                evidence_file_id=item.get("evidence_file_id")
            )
            
            # 异常强制校验：未传照片抛出异常触发整单回滚
            if not item["is_normal"] and not item.get("evidence_file_id"):
                raise BusinessException(
                    code=30002, 
                    message=f"检查项【{item['check_item_name']}】异常，必须上传现场照片"
                )
                
            # 4. 联锁触发生成故障单
            if not item["is_normal"] and generated_fault_id is None:
                fault = FaultRecord(
                    fault_code=f"FLT-{equipment.equipment_code}-{inspection.id}",
                    source_type="INSPECTION_AUTO",
                    equipment_id=equipment_id,
                    snapshot_location_id=equipment.location_id,
                    fault_title=f"巡检发现异常: {item['check_item_name']}",
                    fault_desc=item.get("anomaly_desc") or "日常巡检发现设备部件运行异常",
                    fault_system=equipment.equipment_type, # 默认归属系统
                    fault_part=item["check_item_name"],
                    severity_level=item.get("severity_level", "MAJOR"),
                    status="OPEN",
                    reported_by=user_id
                )
                db.add(fault)
                db.flush()
                generated_fault_id = fault.id
                detail.interlocked_fault_id = generated_fault_id
                
            db.add(detail)
            
        # 5. 设备状态机联动跃迁与下次维护时间推算
        if has_anomaly:
            equipment.status = "FAULTY"
        else:
            equipment.status = "RUNNING"
            # 正常提交更新下次维护日期 = 今天 + 计划周期天数
            equipment.next_maintenance_date = (
                datetime.date.today() + datetime.timedelta(days=equipment.maintenance_interval_days)
            )
            
        if task_id:
            task = db.query(MaintenanceTask).get(task_id)
            if task:
                task.status = "COMPLETED"
                task.completed_at = datetime.datetime.now()
                
        db.commit() # 显式单事务提交
        
        return {
            "inspection_id": inspection.id,
            "has_anomaly": has_anomaly,
            "interlocked_fault_id": generated_fault_id
        }
```

### 3.2 故障抢单认领乐观并发控制 (`FaultClaimService`)
落实第二次反省缺陷 4 与需求 `SWR-FLT-005`：通过原子条件更新规避多位工程师同时接单产生的脏写覆盖。

```python
# backend/app/services/fault_claim.py
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.exceptions import BusinessException

class FaultClaimService:
    @staticmethod
    def claim_fault(db: Session, fault_id: int, engineer_id: int) -> dict:
        """
        原子条件更新 (乐观并发锁):
        仅当工单状态处于 'OPEN' 时更新为 'IN_PROGRESS'。
        若被他人抢先接单，受影响行数为 0，直接抛出业务冲突异常。
        """
        stmt = text("""
            UPDATE fault_records 
            SET status = 'IN_PROGRESS', 
                assigned_engineer_id = :engineer_id, 
                claimed_at = NOW(), 
                updated_at = NOW()
            WHERE id = :fault_id AND status = 'OPEN' AND is_deleted = false
        """)
        
        result = db.execute(stmt, {"engineer_id": engineer_id, "fault_id": fault_id})
        db.commit()
        
        if result.rowcount == 0:
            # 进一步查出究竟被谁认领了，返回友好提示
            current_fault = db.execute(
                text("SELECT u.full_name FROM fault_records f JOIN sys_users u ON f.assigned_engineer_id = u.id WHERE f.id = :id"),
                {"id": fault_id}
            ).fetchone()
            
            claimer_name = current_fault[0] if current_fault else "其他工程师"
            raise BusinessException(
                code=40003, 
                message=f"接单冲突：该故障单已被【{claimer_name}】抢先认领！"
            )
            
        return {"fault_id": fault_id, "status": "IN_PROGRESS"}
```

### 3.3 故障实时智能推荐打分引擎 (`RecommendationEngine`)
落实系统需求 `SWR-FLT-003` 与 `SWR-KB-004`：双阶段混合推荐算法实现。

```python
# backend/app/services/recommend_engine.py
import json
import hashlib
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.redis import redis_client

class RecommendationEngine:
    SIMILARITY_THRESHOLD = 0.60 # 最低置信度阈值 60%
    
    @classmethod
    def get_similar_cases(
        cls, db: Session, equipment_type: str, model_spec: str, fault_desc: str, fault_part: str = ""
    ) -> List[Dict]:
        clean_text = fault_desc.strip().lower()
        if len(clean_text) < 3:
            return []
            
        # 1. 查询 Redis 缓存 (防抖高频拦截)
        cache_key = f"rec:{equipment_type}:{hashlib.md5(clean_text.encode()).hexdigest()}"
        cached = redis_client.get(cache_key)
        if cached is not None:
            return json.loads(cached)
            
        # 2. 第一阶段：元数据硬过滤 + PostgreSQL pg_trgm 快速粗筛 (Top 30)
        query = text("""
            SELECT id, article_code, equipment_model, fault_system, fault_title, 
                   fault_phenomenon, root_cause, solution_steps, is_featured,
                   similarity(fault_phenomenon, :text) AS text_sim
            FROM knowledge_articles
            WHERE equipment_type = :eq_type AND is_deleted = false
            ORDER BY text_sim DESC
            LIMIT 30;
        """)
        
        candidates = db.execute(query, {"eq_type": equipment_type, "text": clean_text}).fetchall()
        
        # 3. 第二阶段：加权综合打分模型
        scored_results = []
        for row in candidates:
            s_text = float(row.text_sim or 0.0)
            i_model = 1.0 if row.equipment_model.lower() == model_spec.lower() else (
                0.5 if model_spec.lower() in row.equipment_model.lower() else 0.0
            )
            i_part = 0.0
            if fault_part and row.fault_system:
                i_part = 1.0 if row.fault_system.lower() == fault_part.lower() else (
                    0.5 if fault_part.lower() in row.fault_system.lower() else 0.0
                )
            i_featured = 1.0 if row.is_featured else 0.0
            
            # 算法权重公式 (SWR-KB-004)
            final_score = (0.50 * s_text) + (0.20 * i_model) + (0.20 * i_part) + (0.10 * i_featured)
            
            if final_score >= cls.SIMILARITY_THRESHOLD:
                scored_results.append({
                    "article_id": row.id,
                    "title": row.fault_title,
                    "match_score": round(final_score * 100, 1), # 输出百分比，如 88.5%
                    "root_cause": row.root_cause,
                    "solution_steps": row.solution_steps,
                    "is_featured": row.is_featured
                })
                
        # 按得分倒序截取前 3 条
        scored_results.sort(key=lambda x: x["match_score"], reverse=True)
        top_3 = scored_results[:3]
        
        # 4. 写入 Redis 缓存 (若为空写入空数组防穿透，TTL=60s；命中写入正常缓存 TTL=600s)
        ttl = 600 if top_3 else 60
        redis_client.setex(cache_key, ttl, json.dumps(top_3))
        
        return top_3
```

### 3.4 非连续运转设备每日运行工时计量与预测性预警引擎 (`EquipmentMeterService`)
落实系统需求 `SWR-MNT-012` 与 `REQ-MNT-012`：针对非 24x7 连续运转设备，以实际开机小时数作为维保触发基准，实现精准计量、临界预警、防重邮件触发与维保派单协同。

#### 1. 业务痛点与架构决策
工业现场存在大量非连续运转机台（如冲压机、注塑辅机、实验机台），若仅采用自然日历倒计时（如720小时=30天），将在设备未达到真实磨损周期时产生虚假维保；若不设管理则易出现超期运转磨损。因此系统引入**设备工时计量引擎（EquipmentMeterService）**：
- **操作员端**：在工控平板“现场维护单 / 设备运行工时填报”视图每日快捷打卡录入开机工时（支持 +4h/+8h/+12h 快速预设，单日累计上限 24.0 小时校验）。
- **后台服务层**：利用行级悲观锁与原子累加保证并发写入一致性，并固化历史填报流水日志（`equipment_operating_logs`）。
- **预警与派单引擎**：实时计算 `current_operating_hours` 与 `interval_hours - advance_warning_hours` 的阈值关系。一旦达到临界预警（例如 720h 周期提前 48h，即 672h），系统启动防重邮件调度，自动向维护主管与责任工程师投递提醒，并生成状态为 `PENDING` 的现场维护工单。
- **闭环清零重置**：当技术人员完成该机台维护单打卡（`InspectionAtomicService` 判定全项合格归档）时，单事务内自动将 `equipment.current_operating_hours` 归零，启动下一轮维保周期。

```python
# backend/app/services/equipment_meter.py
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.equipment import Equipment, EquipmentOperatingLog
from app.models.maintenance import MaintenancePlan, MaintenanceTask
from app.schemas.equipment import EquipmentOperatingLogCreateRequest
from app.core.exceptions import BusinessException

class EquipmentMeterService:
    @classmethod
    def record_operating_hours(cls, db: Session, user, req: EquipmentOperatingLogCreateRequest) -> dict:
        log_date = req.log_date or date.today()
        # 1. 悲观行级锁查询设备
        equipment = db.query(Equipment).filter(Equipment.id == req.equipment_id, Equipment.is_deleted == False).with_for_update().first()
        if not equipment:
            raise BusinessException(code=20005, message="设备不存在或已被软删除")

        # 2. 校验单日累计工时不得超过 24.0 小时
        day_logged = db.query(func.coalesce(func.sum(EquipmentOperatingLog.duration_hours), 0.0)).filter(
            EquipmentOperatingLog.equipment_id == req.equipment_id,
            EquipmentOperatingLog.log_date == log_date
        ).scalar()
        if float(day_logged) + req.duration_hours > 24.0:
            raise BusinessException(code=30006, message=f"单日累计运行工时不能超过 24.0 小时 (当日已填报 {float(day_logged):.1f}h)")

        # 3. 原子累加设备当前运行工时
        equipment.current_operating_hours = round(float(equipment.current_operating_hours or 0.0) + req.duration_hours, 2)

        # 4. 插入工时填报流水记录
        log_entry = EquipmentOperatingLog(
            equipment_id=equipment.id,
            log_date=log_date,
            duration_hours=req.duration_hours,
            cumulative_hours=equipment.current_operating_hours,
            proof_image_id=req.proof_image_id,
            operator_id=user.id,
            operator_name=user.full_name or user.username,
            remarks=req.remarks
        )
        db.add(log_entry)

        # 5. 维保工时预警与自动派单判断
        plan = db.query(MaintenancePlan).filter(
            MaintenancePlan.equipment_id == equipment.id,
            MaintenancePlan.trigger_mode == "OPERATING_HOURS",
            MaintenancePlan.is_active == True,
            MaintenancePlan.is_deleted == False
        ).first()

        interval_hours = plan.interval_hours if plan else (equipment.maintenance_interval_hours or 720)
        advance_warning_hours = plan.advance_warning_hours if plan else 48
        warning_threshold = max(0, interval_hours - advance_warning_hours)

        triggered_maintenance = False
        if equipment.current_operating_hours >= warning_threshold:
            triggered_maintenance = True
            # 防重触发邮件提醒与自动生成现场维护工单
            cls._trigger_warning_notice_and_task(db, equipment, plan, interval_hours)

        db.commit()
        return {
            "equipment_id": equipment.id,
            "current_operating_hours": equipment.current_operating_hours,
            "triggered_maintenance": triggered_maintenance
---

## 4. 设备参数自由文本建模与灵活扩展设计 (取代死板11类Schema强校验)

### 4.1 业务背景与架构重构
工业现场设备型号与非标规格千差万别，原“11类设备专有参数强校验 Schema”存在严重局限性：
1. **穷举困难与场景受限**：现场设备（如特种成型机、真空泵、定制机械手）无法完全归入预设的 11 类模型中。
2. **强校验频发阻断**：技术员填报设备时，由于字段格式微小出入（如非标准 IP 格式、多段转速描述）导致 400 校验异常，严重影响设备建档效率。
3. **参数模型解耦**：将原死板的固定字段 Schema 校验彻底废除，改用**「设备参数信息」自由多行文本 (`params_text: TEXT`)**，用户可自由输入任意维度的专有技术指标、控制协议与工况要求。

### 4.2 数据表持久化与 Schema 定义
```python
# 1. 数据库模型: backend/app/models/equipment.py
class Equipment(BaseAuditModel):
    __tablename__ = "equipments"
    
    equipment_code = Column(String(64), unique=True, nullable=False, index=True)
    equipment_name = Column(String(128), nullable=False, index=True)
    model_spec = Column(String(128), nullable=False)
    location_id = Column(BigInteger, ForeignKey("equipment_locations.id"), nullable=False)
    rated_voltage = Column(String(64), nullable=True) # 额定电压 (如: 380V)
    params_text = Column(Text, nullable=True) # 设备参数信息 (用户自由纯文本)
    status = Column(String(32), default="RUNNING", nullable=False)
    current_operating_hours = Column(Numeric(10, 2), default=0.0)

# 2. Pydantic 请求模型: backend/app/schemas/equipment.py
class EquipmentCreateRequest(BaseModel):
    equipment_code: str = Field(..., min_length=2, max_length=64)
    equipment_name: str = Field(..., min_length=2, max_length=128)
    location_id: int
    model_spec: str = Field(..., min_length=1, max_length=128)
    rated_voltage: Optional[str] = Field("380V", max_length=64)
    params_text: Optional[str] = Field(None, description="设备参数信息(自由文本)")
    params: Optional[Dict[str, Any]] = None # 向后兼容字段
```

### 4.3 表单交互与回显设计
- **录入表单**：前端录入弹窗提供大文本域（TextArea），技术人员可直接拷贝贴入设备说明书技术参数、PLC 配置参数或运行工况指标。
- **列表回显**：表格提供“查看参数信息”按钮，点击后弹窗采用 `<pre>` 样式高亮呈现结构化自由文本。
- **平滑兼容性**：数据库保留旧版 `equipment_params` 表，创建设备时自动将 `params_text` 镜像存入 `extra_params={"text": req.params_text}`，确保已有存量数据与报表系统平滑兼容。

---

## 5. 后台守护调度任务设计 (Background Workers)

落实第二次反省缺陷 5、第三次反省缺陷 8 与需求 `SWR-MNT-004`, `SWR-FLT-008`, `SWR-SYS-006`。

### 5.1 维护倒计时游标分块批处理 (`maintenance_countdown_worker`)
```python
# backend/app/tasks/maintenance_cron.py
import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.equipment import Equipment
from app.models.maintenance import MaintenanceTask
import logging

logger = logging.getLogger(__name__)

def run_daily_maintenance_countdown_job():
    """
    每日凌晨 00:01 执行：
    采用游标分块迭代 (ChunkSize=100)，单设备异常隔离，防止内存溢出与全局事务悬挂
    """
    db: Session = SessionLocal()
    today = datetime.date.today()
    chunk_size = 100
    offset = 0
    
    logger.info("开始执行每日维护倒计时扫描调度...")
    
    try:
        while True:
            # 过滤排除报废与停机的设备
            equipments = db.query(Equipment).filter(
                Equipment.status.in_(["RUNNING", "MAINTENANCE_PENDING"]),
                Equipment.is_deleted == False
            ).order_by(Equipment.id).offset(offset).limit(chunk_size).all()
            
            if not equipments:
                break
                
            for eq in equipments:
                try:
                    if eq.next_maintenance_date is None:
                        continue
                        
                    delta_days = (eq.next_maintenance_date - today).days
                    
                    # 到期当天：状态自动跃迁为待维护，生成待办工单 (幂等)
                    if delta_days <= 0 and eq.status == "RUNNING":
                        eq.status = "MAINTENANCE_PENDING"
                        
                        # 检查今日是否已生成任务防重
                        exist_task = db.query(MaintenanceTask).filter(
                            MaintenanceTask.equipment_id == eq.id,
                            MaintenanceTask.scheduled_date == today,
                            MaintenanceTask.status == "PENDING"
                        ).first()
                        
                        if not exist_task:
                            new_task = MaintenanceTask(
                                task_code=f"TSK-{eq.equipment_code}-{today.strftime('%Y%m%d')}",
                                plan_id=eq.default_plan_id or 1,
                                equipment_id=eq.id,
                                assigned_tech_id=eq.responsible_engineer_id,
                                plan_version_snapshot="V1.0",
                                scheduled_date=today,
                                due_date=today + datetime.timedelta(days=3), # 3天宽限期
                                status="PENDING"
                            )
                            db.add(new_task)
                            
                    db.commit() # 单台设备提交，异常隔离
                except Exception as ex:
                    db.rollback()
                    logger.error(f"处理设备 ID={eq.id} 维护调度发生异常: {str(ex)}")
                    
            offset += chunk_size
            
        logger.info("每日维护倒计时扫描调度完成！")
    finally:
        db.close()
```

### 5.2 磁盘孤儿未关联文件定期清理守护任务 (`orphan_file_cleaner_worker`)
```python
# backend/app/tasks/file_cleaner.py
import os
import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.equipment import EquipmentFile
import logging

logger = logging.getLogger(__name__)

def run_orphan_files_cleanup_job():
    """
    每日凌晨 03:00 执行：
    清理上传超过 24 小时且仍未被业务表单关联引用的孤儿文件 (is_linked == False)
    """
    db: Session = SessionLocal()
    expire_time = datetime.datetime.now() - datetime.timedelta(hours=24)
    
    try:
        orphan_files = db.query(EquipmentFile).filter(
            EquipmentFile.is_linked == False,
            EquipmentFile.created_at < expire_time
        ).limit(500).all()
        
        for f in orphan_files:
            try:
                # 物理删除磁盘文件
                if os.path.exists(f.storage_path):
                    os.remove(f.storage_path)
                # 移除数据库记录
                db.delete(f)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"删除孤儿文件 {f.storage_path} 失败: {str(e)}")
                
        logger.info(f"清理孤儿文件完成，共释放 {len(orphan_files)} 个未关联过期附件")
    finally:
        db.close()
```

---

## 6. 前端工程、状态流转与触控视图组件设计

### 6.1 前端路由权限与强制改密拦截器 (Router Guard)
```typescript
// frontend/src/router/guard.ts
import { Router } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

export function setupRouterGuard(router: Router) {
  router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore();
    
    if (to.path === '/login') {
      return next();
    }
    
    // 1. 登录凭据检查
    if (!authStore.token) {
      return next({ path: '/login', query: { redirect: to.fullPath } });
    }
    
    // 2. 强制改密严格阻断 (REQ-USR-004 / 第一次反省缺陷 2)
    if (authStore.userInfo?.force_change_password) {
      if (to.path !== '/force-change-password') {
        return next('/force-change-password');
      }
      return next(); // 放行改密页面
    }
    
    // 3. 按钮与路由角色权限拦截 (RBAC)
    if (to.meta.roles) {
      const allowedRoles = to.meta.roles as string[];
      if (!allowedRoles.includes(authStore.userInfo.role_code)) {
        return next('/403');
      }
    }
    
    next();
  });
}
```

#### 6.2 工控平板现场维护单交互组件设计
针对车间现场震动、戴手套操作及工控平板分辨率（$1280 \times 800$）进行特定 CSS 与交互设计：
* **单手触控优化**：按钮垂直点击热区高度 $\ge 48\text{px}$，间距 $\ge 16\text{px}$。
* **单选卡片样式**：绿色大号“正常”按钮与高警示红“异常”按钮采用分屏大色块，杜绝误触。
* **工单编辑与工作完成证据上传**：技术员接单后，在表单中直接开放工单处理说明编辑输入框，并配置多图上传组件用于留存工作完成现场证据。
* **即拍即传浮窗**：点击异常项后，界面自动平滑锚点滑动至必填照片上传区域，带相机图标指引。

### 6.3 SMTP 邮件服务器可视化配置与动态生效机制 (SWR-SYS-001)
* **前端交互 (`SystemSettingsView.vue`)**：
  - 提供 SMTP 主机、端口、发信认证账号、密码/授权码、发件人昵称及 SSL/STARTTLS 协议开关的可视化配置表单。
  - **密码脱敏保护**：获取配置时返回 `smtp_pass_masked: "******"`；提交表单时若未输入新密码（保留 `******`），后端自动保持数据库中已加密/存储的原始授权码，实现无损脱敏编辑。
  - **即时在线连通性自检**：提供目标邮箱输入与“发送自检测试”按钮，支持使用已保存配置或实时表单草稿参数进行网络通信握手自检。
* **数据持久化与热重载 (`SystemSmtpConfig` + `EmailService`)**：
  - 映射实体表 `sys_smtp_configs`，记录动态发信参数，每次页面提交即时落盘。
  - 后台调度任务（维保提前提醒批处理、SLA 逾期告警升级）调用 `EmailService.send_email` 时动态拉取当前启用的配置，无需重启后端服务即可热生效。
  - 任何配置更新动作通过 `AuditLog` 自动记录到 180 天防篡改操作审计流水中。

### 6.4 细粒度角色控制与按钮级 `v-permission` DOM 物理移除指令 (SWR-USR-001)
为满足工业现场“操作入口与权限严格匹配、未授权功能直接关闭杜绝报错弹窗”的交互要求，前端工程构建了三层联动防御体系：

1. **侧边栏导航菜单收敛 (`Layout.vue`)**：
   - 管理员专用模块（“用户管理”、“系统设置”）在侧边栏模板中绑定 `v-if="authStore.isAdmin"`。
   - 非管理员角色（`ENGINEER`、`TECHNICIAN`）登录后，侧边栏完全不渲染受限菜单入口（系统精简内置三大角色，不设车间主管）。

2. **全局自定义权限指令 (`directives/permission.ts`)**：
   - 前端全局注册 `v-permission` 自定义指令，在元素挂载生命周期检测当前登录用户角色：
   ```typescript
   export const permissionDirective: Directive = {
     mounted(el: HTMLElement, binding: DirectiveBinding) {
       const { value } = binding;
       const authStore = useAuthStore();
       const userRole = authStore.userInfo?.role_code;
       if (value) {
         const allowedRoles = Array.isArray(value) ? value : [value];
         const hasPermission = !!userRole && allowedRoles.includes(userRole);
         if (!hasPermission) {
           // 直接从 DOM 树物理移除节点，杜绝未授权按钮引起 403 弹窗
           el.parentNode?.removeChild(el);
         }
       }
     }
   };
   ```

3. **视图核心受控按钮绑定与技术员权限开放**：
   - 设备信息视图 (`EquipmentListView.vue`)：“录入设备信息”、“导出Excel”、表格行“删除”绑定 `v-permission="['ADMIN', 'ENGINEER']"`。
   - 设备维护计划视图 (`MaintenancePlanView.vue`)：“编制新维护计划”（最小单位小时）、表格行“升级版本快照”绑定 `v-permission="['ADMIN', 'ENGINEER']"`。
   - 现场维护单视图 (`InspectionView.vue`)：技术员接单后开放“编辑工单信息”输入框与“上传工作完成证据图片”组件。
   - 技能实训视图 (`TrainingView.vue`)：“编制实操新课程”绑定 `v-permission="['ADMIN', 'ENGINEER']"`。
   - 故障流转看板 (`FaultKanbanView.vue`)：“并发抢单认领”、“维修复盘提交”、“验收归档关闭”绑定 `v-permission="['ADMIN', 'ENGINEER']"`。
   - 知识库视图 (`KnowledgeView.vue`)：“录入知识条目”绑定 `v-permission="['ADMIN', 'ENGINEER']"`。

4. **路由守卫硬拦截 (`router/guard.ts`)**：
   - 针对直接在浏览器地址栏输入受限 URL（如 `/users`）的行为，路由守卫拦截 `to.meta.roles`，非授权角色直接阻断并重定向至 403 页面，不向后端发出任何非法 API 请求。

---

## 7. 软件设计追踪矩阵 (SWR to SDD Traceability)

| 软件需求编号 | 需求名称 | 详细设计模块 (Module & Class) | 核心实现代码/类文件路径 | 单元测试用例编号 |
|:---|:---|:---|:---|:---|
| **SWR-USR-001** | 三大角色权限控制与无权限直接关闭 | `deps.require_role`, `v-permission` | `backend/app/api/deps.py`, `frontend/src/directives/permission.ts` | `TEST-USR-001` |
| **SWR-USR-002** | 全局设备协同与免工种数据隔离 | 全局协同查询路由 | `backend/app/api/v1/equipments.py` | `TEST-USR-002` |
| **SWR-USR-003** | 账号全生命周期与软禁用/软删除 | `UserService`, `UsersRouter` (不设车间主管与工种隔离) | `backend/app/api/v1/users.py`, `frontend/src/views/UserManagementView.vue` | `TEST-USR-003` |
| **SWR-USR-004** | 强制改密双重阻断 | `JWT Auth Middleware`, `Router Guard` | `backend/app/core/security.py` | `TEST-USR-004` |
| **SWR-USR-005** | 邮箱重置一次性Token | `Redis Token Service` | `backend/app/core/redis.py` | `TEST-USR-005` |
| **SWR-USR-006** | 防暴破锁定与8小时生产会话 | `LoginAttemptLimiter` + 480分钟单班次Token | `backend/app/core/security.py`, `backend/app/core/config.py` | `TEST-USR-006` |
| **SWR-USR-007** | 全局操作人审计自动注入 | `AuditModelListener` | `backend/app/models/base.py` | `TEST-USR-007` |
| **SWR-USR-008** | 操作级细粒度权限校验 | `ActionPermissionChecker` | `backend/app/api/deps.py` | `TEST-USR-008` |
| **SWR-DEV-001** | 4级层级拓扑树 (工厂/部门/系统/设备) | `LocationTreeService.validate_path` | `backend/app/services/location.py` | `TEST-DEV-001` |
| **SWR-DEV-002** | 层级防孤儿删除校验 | `LocationRepository.delete` | `backend/app/repositories/location.py` | `TEST-DEV-002` |
| **SWR-DEV-003** | 设备信息精简录入 (免工种/类型冗余) | `EquipmentCreateSchema` | `backend/app/schemas/equipment.py` | `TEST-DEV-003` |
| **SWR-DEV-004** | 设备参数自由文本建模与展示 | `params_text` 自由文本扩展 | `backend/app/schemas/equipment.py` | `TEST-DEV-004` |
| **SWR-DEV-005** | 设备状态机流转引擎 | `EquipmentStateMachine` | `backend/app/services/state_machine.py` | `TEST-DEV-005` |
| **SWR-DEV-006** | 附件解耦与工作证据标记 | `EquipmentFile.is_linked` | `backend/app/services/file.py` | `TEST-DEV-006` |
| **SWR-DEV-007** | 设备多维组合过滤 | `EquipmentFilterSpecification` | `backend/app/repositories/equipment.py` | `TEST-DEV-007` |
| **SWR-DEV-008** | 电子履历时间线聚合 | `TimelineAggregatorService` | `backend/app/services/equipment.py` | `TEST-DEV-008` |
| **SWR-DEV-009** | Excel流式导入与预览 | `ExcelStreamProcessor` | `backend/app/services/excel_processor.py`| `TEST-DEV-009` |
| **SWR-MNT-001** | 设备维护计划与维护内容编制 | `MaintenancePlanService` (最小单位小时) | `backend/app/services/maintenance.py` | `TEST-MNT-001` |
| **SWR-MNT-002** | 设备维护内容与标准配图比对 | `ChecklistRendererComponent` | `frontend/src/components/Checklist.vue` | `TEST-MNT-002` |
| **SWR-MNT-003** | 维护计划版本快照固化 | `MaintenancePlanService.bump_version` | `backend/app/services/maintenance.py` | `TEST-MNT-003` |
| **SWR-MNT-004** | 动态倒计时分块游标批处理 (小时级) | `maintenance_countdown_worker` | `backend/app/tasks/maintenance_cron.py`| `TEST-MNT-004` |
| **SWR-MNT-005** | 维护邮件防重幂等校验 | `EmailDispatcher.send_maintenance_notice` | `backend/app/tasks/email_dispatcher.py` | `TEST-MNT-005` |
| **SWR-MNT-006** | 到期现场维护单自动派单 | `maintenance_task_trigger` | `backend/app/tasks/maintenance_cron.py`| `TEST-MNT-006` |
| **SWR-MNT-007** | 现场维护单、工单编辑与证据上传 | `InspectionTouchView`, `TaskEditProofDialog` | `frontend/src/views/Inspection.vue` | `TEST-MNT-007` |
| **SWR-MNT-008** | 维护异常单事务联锁提单 | `InspectionAtomicService.submit_inspection` | `backend/app/services/inspection_tx.py` | `TEST-MNT-008` |
| **SWR-MNT-009** | 维护超时持续催办轮询 | `maintenance_overdue_checker` | `backend/app/tasks/maintenance_cron.py`| `TEST-MNT-009` |
| **SWR-MNT-010** | 维护完成率聚合与ECharts | `CompletionRateAggregator` | `backend/app/services/statistics.py` | `TEST-MNT-010` |
| **SWR-MNT-011** | 现场维护明细报表导出 | `InspectionExportService` | `backend/app/services/excel_processor.py`| `TEST-MNT-011` |
| **SWR-MNT-012** | 非连续运转设备工时累计与预警引擎 | `EquipmentMeterService` + `InspectionTouchView` | `backend/app/services/equipment_meter.py`, `frontend/src/views/InspectionTouchView.vue` | `TEST-MNT-012` |
| **SWR-FLT-001** | 故障双来源适配接入 | `FaultIngestionService` | `backend/app/services/fault.py` | `TEST-FLT-001` |
| **SWR-FLT-002** | 故障要素录入与照片强制 | `FaultCreateSchema` | `backend/app/schemas/fault.py` | `TEST-FLT-002` |
| **SWR-FLT-003** | 实时智能排查防抖推荐 | `RecommendationEngine` + Redis | `backend/app/services/recommend_engine.py` | `TEST-FLT-003` |
| **SWR-FLT-004** | 故障生命周期状态机 | `FaultStateMachine` | `backend/app/services/state_machine.py` | `TEST-FLT-004` |
| **SWR-FLT-005** | 故障并发接单乐观锁 | `FaultClaimService.claim_fault` | `backend/app/services/fault_claim.py` | `TEST-FLT-005` |
| **SWR-FLT-006** | 根因与解决步骤强校验 | `FaultResolveSchema` | `backend/app/schemas/fault.py` | `TEST-FLT-006` |
| **SWR-FLT-007** | 标定典型故障案例 | `FaultService.toggle_featured` | `backend/app/services/fault.py` | `TEST-FLT-007` |
| **SWR-FLT-008** | SLA 响应时效轮询器 | `sla_monitor_worker` | `backend/app/tasks/sla_monitor.py` | `TEST-FLT-008` |
| **SWR-FLT-009** | 故障明细复盘导出 | `FaultExportService` | `backend/app/services/excel_processor.py`| `TEST-FLT-009` |
| **SWR-KB-001** | 故障关闭异步事件沉淀 | `FaultClosedDomainListener` | `backend/app/services/knowledge.py` | `TEST-KB-001` |
| **SWR-KB-002** | PostgreSQL pg_trgm 检索 | `KnowledgeSearchService` | `backend/app/services/knowledge.py` | `TEST-KB-002` |
| **SWR-KB-003** | 知识库多维 Facet 聚合 | `KnowledgeFacetFilterComponent` | `frontend/src/views/Knowledge.vue` | `TEST-KB-003` |
| **SWR-KB-004** | 双阶段混合推荐算法实现 | `RecommendationEngine` | `backend/app/services/recommend_engine.py` | `TEST-KB-004` |
| **SWR-KB-005** | 知识条目人工精编与打标 | `KnowledgeAdminService` | `backend/app/services/knowledge.py` | `TEST-KB-005` |
| **SWR-KB-006** | 知识手册 Excel 导出 | `KnowledgeExportService` | `backend/app/services/excel_processor.py`| `TEST-KB-006` |
| **SWR-TRN-001** | 培训课程编制与多媒体上传 | `TrainingCourseService` | `backend/app/services/training.py` | `TEST-TRN-001` |
| **SWR-TRN-002** | 课程挂接典型真实案例 | `CourseCaseLinker` | `backend/app/services/training.py` | `TEST-TRN-002` |
| **SWR-TRN-003** | 培训实施签到与现场影像 | `TrainingRecordService` | `backend/app/services/training.py` | `TEST-TRN-003` |
| **SWR-TRN-004** | 考核打分与复训状态触发 | `UserScoreEvaluator` | `backend/app/services/training.py` | `TEST-TRN-004` |
| **SWR-TRN-005** | 员工终身技能电子档案卡 | `UserProfileAggregator` | `backend/app/services/training.py` | `TEST-TRN-005` |
| **SWR-DSH-001** | FCM设备运维管理平台(数据平台)卡片 | `DashboardMetricService` | `backend/app/services/dashboard.py` | `TEST-DSH-001` |
| **SWR-DSH-002** | 角色差异化待办推送 | `UserTodoRouterService` | `backend/app/services/dashboard.py` | `TEST-DSH-002` |
| **SWR-DSH-003** | 故障趋势与完成率图表 | `DashboardChartService` | `backend/app/services/dashboard.py` | `TEST-DSH-003` |
| **SWR-DSH-004** | 全局高频快捷动作入口 | `QuickActionFabComponent` | `frontend/src/components/QuickAction.vue`| `TEST-DSH-004` |
| **SWR-SYS-001** | SMTP 页面可视化配置与自检发信 | `SystemSmtpConfig` + `EmailService` + `SystemSettingsView` | `backend/app/models/system.py`, `frontend/src/views/SystemSettingsView.vue` | `TEST-SYS-001` |
| **SWR-SYS-002** | 通知分组与邮件路由 | `NotificationRoutingService` | `backend/app/services/system.py` | `TEST-SYS-002` |
| **SWR-SYS-003** | 全生命周期邮件调度队列 | `EmailQueueWorker` | `backend/app/tasks/email_dispatcher.py` | `TEST-SYS-003` |
| **SWR-SYS-004** | 通用 Excel 流式解析底座 | `OpenpyxlStreamEngine` | `backend/app/services/excel_processor.py`| `TEST-SYS-004` |
| **SWR-SYS-005** | 180天只读操作审计日志 | `AuditMiddleware` (JSON Diff) | `backend/app/core/audit.py` | `TEST-SYS-005` |
| **SWR-SYS-006** | 文件魔数校验与孤儿清理 | `FileValidator` + `orphan_cleaner` | `backend/app/tasks/file_cleaner.py` | `TEST-SYS-006` |
| **SWR-NFR-001** | 密码加盐与防暴力破解 | `bcrypt` (Cost=12) + `Redis Limiter` | `backend/app/core/security.py` | `TEST-NFR-001` |
| **SWR-NFR-002** | 软件性能指标基准保障 | 数据库复合索引 + Redis 缓存 | `backend/app/models/` | `TEST-NFR-002` |
| **SWR-NFR-003** | 1000台设备容量压测保障 | PostgreSQL Connection Pool | `backend/app/core/database.py` | `TEST-NFR-003` |
| **SWR-NFR-004** | 软删除基类与单事务一致性 | `BaseAuditModel` + 本地事务 | `backend/app/models/base.py` | `TEST-NFR-004` |
| **SWR-NFR-005** | 工控平板触控与浏览器适配 | 响应式 CSS + 48px 热区 | `frontend/src/styles/touch.css` | `TEST-NFR-005` |

---
*(本文档为 MaintainWise 软件编码工程实现的终极权威技术标准)*