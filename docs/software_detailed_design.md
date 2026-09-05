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
4. [强类型 Pydantic Schema 校验建模 (11类设备专有模型)](#4-强类型-pydantic-schema-校验建模-11类设备专有模型)
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
│   │   │   │   ├── users.py        # 用户管理 CRUD
│   │   │   │   ├── locations.py    # 5级位置树 API
│   │   │   │   ├── equipments.py   # 设备台账、参数、履历与导入导出
│   │   │   │   ├── maintenance.py  # 维护计划、任务、巡检原子打卡提交
│   │   │   │   ├── faults.py       # 故障报修、接单乐观锁、复盘关闭
│   │   │   │   ├── knowledge.py    # 知识库全文检索、智能推荐打分
│   │   │   │   ├── training.py     # 培训课程、挂接案例、实训考核
│   │   │   │   ├── dashboard.py    # 仪表盘统计卡片、角色工作台待办
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
│   │   │   ├── inspection.py       # 巡检原子打卡 Payload Schema
│   │   │   ├── fault.py            # 故障录入与复盘 Schema
│   │   │   └── common.py           # 分页响应包与标准结果返回封包
│   │   ├── services/               # 领域业务服务层
│   │   │   ├── state_machine.py    # 设备与故障有限状态机服务
│   │   │   ├── inspection_tx.py    # 巡检异常联锁单事务提单服务
│   │   │   ├── fault_claim.py      # 故障接单乐观并发控制服务
│   │   │   ├── recommend_engine.py # 双阶段故障智能推荐打分引擎
│   │   │   └── excel_processor.py  # 流式 Excel 导入导出解析器
│   │   └── tasks/                  # 异步守护与定时调度任务 (APScheduler / Celery)
│   │       ├── maintenance_cron.py # 维护倒计时游标分块扫描与派单
│   │       ├── email_dispatcher.py # 邮件防重调度投递
│   │       ├── sla_monitor.py      # SLA 超时监控轮询
│   │       └── file_cleaner.py     # 24小时未关联孤儿文件清理任务
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                       # 前端交互工程 (Vue 3 / Vite / TypeScript / Element Plus)
│   ├── src/
│   │   ├── api/                    # Axios API 请求封装与全局拦截器
│   │   ├── components/             # 通用业务组件 (图片比对浮窗、时间线、参数渲染器)
│   │   ├── router/                 # Vue Router 路由定义与强制改密守卫 (Route Guard)
│   │   ├── stores/                 # Pinia 状态管理 (Auth, Todo, Equipment, Inspection)
│   │   ├── views/                  # 业务页面 (仪表盘、巡检打卡、设备台账、故障复盘)
│   │   └── styles/                 # 工业触控适配 CSS (48px 触控热区)
│   ├── Dockerfile
│   └── package.json
└── deploy/                         # 容器化与运维脚本 (Nginx, Postgres, Scripts)
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
| **20001** | 400 | `CANNOT_DELETE_NODE_WITH_CHILDREN` | 目标位置节点存在子节点或下挂设备，禁止物理删除 |
| **20002** | 400 | `EQUIPMENT_CODE_DUPLICATE` | 设备编码已存在，请更换唯一编码 |
| **20003** | 400 | `CYCLIC_HIERARCHY_DETECTED` | 拓扑位置修改失败：检测到循环依赖成环路径 |
| **20004** | 400 | `MAX_DEPTH_EXCEEDED` | 位置层级深度超出限制，系统最高仅支持 5 级 |
| **20005** | 400 | `INVALID_STATUS_TRANSITION` | 设备生命周期状态跃迁非法（如报废设备不可恢复为正常） |
| **20006** | 400 | `EQUIPMENT_PARAM_INVALID` | 设备专有参数校验不合法（如 IP 格式错误或风量为负数） |
| **30001** | 400 | `INSPECTION_ITEM_MISSING` | 巡检打卡失败：存在未评定的检查清单项 |
| **30002** | 400 | `INSPECTION_ANOMALY_PHOTO_REQUIRED` | 检查项判定为异常时，必须强制上传现场照片证据 |
| **30003** | 400 | `PLAN_VERSION_CONFLICT` | 维护计划版本冲突，当前计划正在被其他管理员修改 |
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
        cls, db: Session, equipment_type: str, model_spec: str, fault_desc: str
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
            i_featured = 1.0 if row.is_featured else 0.0
            
            # 算法权重公式
            final_score = (0.50 * s_text) + (0.30 * i_model) + (0.20 * i_featured)
            
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

---

## 4. 强类型 Pydantic Schema 校验建模 (11类设备专有模型)

落实第一次反省缺陷 1 与需求 `SWR-DEV-004`：杜绝脏数据注入，建立分类型严格 Schema 校验器。

```python
# backend/app/schemas/equipment_params.py
from pydantic import BaseModel, Field, IPvAnyAddress, field_validator
from typing import Optional, Dict, Any, Literal

# 1. 基础通用参数基类
class BaseEquipmentParamSchema(BaseModel):
    extra_params: Optional[Dict[str, Any]] = Field(default_factory=dict)

# 2. PLC 专有参数强校验模型
class PLCEquipmentParamSchema(BaseEquipmentParamSchema):
    cpu_model: str = Field(..., min_length=2, max_length=64, description="CPU型号，如 S7-1200 CPU 1214C")
    ip_address: str = Field(..., description="合法的工业IPv4地址")
    comm_protocol: Literal["PROFINET", "MODBUS_TCP", "ETHERNET_IP", "OPC_UA", "MPI"] = Field(..., description="支持的工业总线协议")
    io_points_spec: str = Field(..., min_length=2, max_length=128, description="I/O点数规格，如 14DI/10DO/2AI")
    firmware_version: Optional[str] = Field(None, max_length=32)

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        import ipaddress
        try:
            ipaddress.IPv4Address(v)
        except ValueError:
            raise ValueError(f"【{v}】不是合法的IPv4网络地址")
        return v

# 3. 风机专有参数强校验模型
class FanEquipmentParamSchema(BaseEquipmentParamSchema):
    air_volume_m3h: float = Field(..., gt=0, description="额定风量 (m³/h)，必须大于0")
    air_pressure_pa: float = Field(..., gt=0, description="额定全压 (Pa)，必须大于0")
    rated_power_kw: float = Field(..., gt=0, description="轴功率 (kW)")
    rated_speed_rpm: int = Field(..., gt=0, le=30000, description="额定转速 (rpm)")
    drive_type: Literal["DIRECT", "BELT", "COUPLING"] = Field(..., description="驱动方式: 直联/皮带/联轴器")

# 4. 电机专有参数强校验模型
class MotorEquipmentParamSchema(BaseEquipmentParamSchema):
    rated_power_kw: float = Field(..., gt=0, description="额定功率 (kW)")
    rated_voltage_v: float = Field(..., gt=0, description="额定电压 (V)")
    rated_current_a: float = Field(..., gt=0, description="额定电流 (A)")
    rated_speed_rpm: int = Field(..., gt=0, le=10000, description="额定转速 (rpm)")
    insulation_class: Literal["A", "E", "B", "F", "H", "C"] = Field(..., description="绝缘等级")
    protection_level: Literal["IP54", "IP55", "IP65", "IP67"] = Field(..., description="外壳防护等级")

# 5. 传感器专有参数强校验模型
class SensorEquipmentParamSchema(BaseEquipmentParamSchema):
    measurement_type: Literal["TEMPERATURE", "PRESSURE", "FLOW", "LEVEL", "PHOTOELECTRIC", "PROXIMITY"] = Field(...)
    measurement_range: str = Field(..., min_length=1, max_length=64, description="测量量程，如 -50~200℃")
    output_signal_type: Literal["4-20mA", "0-10V", "0-5V", "PNP", "NPN", "RS485", "IO-Link"] = Field(...)
    accuracy_class: str = Field(..., min_length=1, max_length=32, description="精度等级，如 ±0.5%FS")

# 6. 变频器专有参数强校验模型
class InverterEquipmentParamSchema(BaseEquipmentParamSchema):
    rated_power_kw: float = Field(..., gt=0)
    input_voltage_v: float = Field(..., gt=0)
    rated_output_current_a: float = Field(..., gt=0)
    control_mode: Literal["V_F", "VECTOR_OPEN_LOOP", "VECTOR_CLOSED_LOOP", "TORQUE"] = Field(...)
    comm_interface: Literal["MODBUS", "CANOPEN", "PROFINET", "PROFIBUS_DP"] = Field(...)
```

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

### 6.2 工控平板巡检打卡交互组件设计
针对车间现场震动、戴手套操作及工控平板分辨率（$1280 \times 800$）进行特定 CSS 与交互设计：
* **单手触控优化**：按钮垂直点击热区高度 $\ge 48\text{px}$，间距 $\ge 16\text{px}$。
* **单选卡片样式**：绿色大号“正常”按钮与高警示红“异常”按钮采用分屏大色块，杜绝误触。
* **即拍即传浮窗**：点击异常项后，界面自动平滑锚点滑动至必填照片上传区域，带相机图标指引。

---

## 7. 软件设计追踪矩阵 (SWR to SDD Traceability)

| 软件需求编号 | 需求名称 | 详细设计模块 (Module & Class) | 核心实现代码/类文件路径 | 单元测试用例编号 |
|:---|:---|:---|:---|:---|
| **SWR-USR-001** | 角色权限控制 | `deps.require_role`, `v-permission` | `backend/app/api/deps.py` | `TEST-USR-001` |
| **SWR-USR-002** | 工作类型数据过滤 | `apply_work_type_scope` 过滤器 | `backend/app/repositories/base.py` | `TEST-USR-002` |
| **SWR-USR-003** | 账号生命周期与软禁用 | `UserService.update_status` | `backend/app/services/user.py` | `TEST-USR-003` |
| **SWR-USR-004** | 强制改密双重阻断 | `JWT Auth Middleware`, `Router Guard` | `backend/app/core/security.py` | `TEST-USR-004` |
| **SWR-USR-005** | 邮箱重置一次性Token | `Redis Token Service` | `backend/app/core/redis.py` | `TEST-USR-005` |
| **SWR-USR-006** | 防暴破锁定与超时登出 | `LoginAttemptLimiter` | `backend/app/core/security.py` | `TEST-USR-006` |
| **SWR-USR-007** | 全局操作人审计自动注入 | `AuditModelListener` | `backend/app/models/base.py` | `TEST-USR-007` |
| **SWR-USR-008** | 操作级细粒度权限校验 | `ActionPermissionChecker` | `backend/app/api/deps.py` | `TEST-USR-008` |
| **SWR-DEV-001** | 5级位置树防成环算法 | `LocationTreeService.validate_path` | `backend/app/services/location.py` | `TEST-DEV-001` |
| **SWR-DEV-002** | 层级防孤儿删除校验 | `LocationRepository.delete` | `backend/app/repositories/location.py` | `TEST-DEV-002` |
| **SWR-DEV-003** | 设备台账录入校验 | `EquipmentCreateSchema` | `backend/app/schemas/equipment.py` | `TEST-DEV-003` |
| **SWR-DEV-004** | 11类设备专有强校验 | `PLCEquipmentParamSchema` 等 | `backend/app/schemas/equipment_params.py` | `TEST-DEV-004` |
| **SWR-DEV-005** | 设备状态机流转引擎 | `EquipmentStateMachine` | `backend/app/services/state_machine.py` | `TEST-DEV-005` |
| **SWR-DEV-006** | 附件解耦与孤儿标记 | `EquipmentFile.is_linked` | `backend/app/services/file.py` | `TEST-DEV-006` |
| **SWR-DEV-007** | 设备多维组合过滤 | `EquipmentFilterSpecification` | `backend/app/repositories/equipment.py` | `TEST-DEV-007` |
| **SWR-DEV-008** | 电子履历时间线聚合 | `TimelineAggregatorService` | `backend/app/services/equipment.py` | `TEST-DEV-008` |
| **SWR-DEV-009** | Excel流式导入与预览 | `ExcelStreamProcessor` | `backend/app/services/excel_processor.py`| `TEST-DEV-009` |
| **SWR-MNT-001** | 维护计划编制与SOP | `MaintenancePlanService` | `backend/app/services/maintenance.py` | `TEST-MNT-001` |
| **SWR-MNT-002** | 巡检清单标准配图比对 | `ChecklistRendererComponent` | `frontend/src/components/Checklist.vue` | `TEST-MNT-002` |
| **SWR-MNT-003** | 维护计划版本快照固化 | `MaintenancePlanService.bump_version` | `backend/app/services/maintenance.py` | `TEST-MNT-003` |
| **SWR-MNT-004** | 动态倒计时分块游标批处理 | `maintenance_countdown_worker` | `backend/app/tasks/maintenance_cron.py`| `TEST-MNT-004` |
| **SWR-MNT-005** | 维护邮件防重幂等校验 | `EmailDispatcher.send_maintenance_notice` | `backend/app/tasks/email_dispatcher.py` | `TEST-MNT-005` |
| **SWR-MNT-006** | 到期维护任务自动派单 | `maintenance_task_trigger` | `backend/app/tasks/maintenance_cron.py`| `TEST-MNT-006` |
| **SWR-MNT-007** | 车间平板现场打卡视图 | `InspectionTouchView` | `frontend/src/views/Inspection.vue` | `TEST-MNT-007` |
| **SWR-MNT-008** | 巡检异常单事务联锁提单 | `InspectionAtomicService.submit_inspection` | `backend/app/services/inspection_tx.py` | `TEST-MNT-008` |
| **SWR-MNT-009** | 维护超时每日催办轮询 | `maintenance_overdue_checker` | `backend/app/tasks/maintenance_cron.py`| `TEST-MNT-009` |
| **SWR-MNT-010** | 维护完成率聚合与ECharts | `CompletionRateAggregator` | `backend/app/services/statistics.py` | `TEST-MNT-010` |
| **SWR-MNT-011** | 巡检明细全量报表导出 | `InspectionExportService` | `backend/app/services/excel_processor.py`| `TEST-MNT-011` |
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
| **SWR-DSH-001** | 资产健康大盘实时卡片 | `DashboardMetricService` | `backend/app/services/dashboard.py` | `TEST-DSH-001` |
| **SWR-DSH-002** | 角色差异化待办推送 | `UserTodoRouterService` | `backend/app/services/dashboard.py` | `TEST-DSH-002` |
| **SWR-DSH-003** | 故障趋势与完成率图表 | `DashboardChartService` | `backend/app/services/dashboard.py` | `TEST-DSH-003` |
| **SWR-DSH-004** | 全局高频快捷动作入口 | `QuickActionFabComponent` | `frontend/src/components/QuickAction.vue`| `TEST-DSH-004` |
| **SWR-SYS-001** | SMTP 自检发信客户端 | `SmtpClientService` | `backend/app/services/system.py` | `TEST-SYS-001` |
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
