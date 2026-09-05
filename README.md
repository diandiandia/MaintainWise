# MaintainWise 工业设备全生命周期维保协同系统

> **面向离散制造业的现代化设备健康管理、预防性维保、突发抢修协同与经验资产沉淀平台。**  
> 基于 **FastAPI + SQLAlchemy 2.0 + PostgreSQL 16 + Redis 7** 后端架构与 **Vue 3 + TypeScript + Element Plus + ECharts** 工控触控前端构建。

---

## 🚀 两种运行环境与定位 (Dual-Mode Architecture)

MaintainWise 采用高度解耦的**双模运行体系**，完美分离「Linux 宿主机本地直接测试与轻量开发」与「Docker 容器化生产部署」：

| 维度 | 模式 1：Linux 宿主机直接测试与开发 (`linux_local`) | 模式 2：Docker 容器集群生产部署 (`docker_production`) |
|:---|:---|:---|
| **核心定位** | 本地敏捷开发、CI 持续集成流水线、极速单元与E2E测试 | 生产工厂落地、微服务集群交付、高并发高可用保障 |
| **外部依赖要求** | **零外部依赖** (无需预装或启动 PostgreSQL/Redis/Docker) | **标准 Docker 环境** (Docker 24.0+ & Docker Compose V2+) |
| **持久化数据库** | 本地 SQLite 自动回退 (`maintainwise.db` 或内存 `:memory:`) | 独立容器 PostgreSQL 16 (挂载持久卷，启用 `pg_trgm` 向量与中文分词) |
| **高速缓存与队列** | 本地内存 MockRedis 引擎自动降级 | 独立容器 Redis 7 (启用 AOF 持久化与密码强认证) |
| **文件存储路径** | 动态解析至项目根目录 `uploads/` | 容器挂载 `/app/uploads`，由网关 Nginx 反向代理限流 (50MB) |
| **后台定时调度** | 纯净按需调用测试，不阻塞线程 | 后台守护线程自动常驻执行倒计时、SLA 监控与孤儿文件清理 |
| **启动/测试命令** | `make test` 或 `bash deploy/scripts/test_local.sh` | `make deploy` 或 `bash deploy/scripts/deploy.sh` |

---

## 🛠️ 1. Linux 宿主机直接测试指南 (Local Direct Testing)

针对在 Linux 终端环境直接进行代码修改与测试验证的场景：

### 1.1 安装运行依赖
```bash
# 1. 安装 Python 后端测试依赖
pip install -r backend/requirements.txt

# 2. 安装前端构建依赖
npm install --prefix frontend
```

### 1.2 执行一键测试套件
```bash
# 一键运行全量自动化测试 (包含后端 28 项核心业务用例 + 前端 TypeScript 编译与打包)
make test

# 或者直接执行测试脚本:
bash deploy/scripts/test_local.sh
```

### 1.3 模块专项测试
```bash
# 仅运行后端 Pytest 测试
make test-backend
# 或指定运行特定测试文件:
pytest -v backend/tests/test_e2e_integration.py   # 全流程端到端闭环测试
pytest -v backend/tests/test_services.py          # 领域状态机与并发锁测试

# 仅运行前端类型检查与打包构建
make test-frontend
```

---

## 🐳 2. Docker 容器化集群一键部署指南 (Docker Production)

针对工厂车间服务器或生产环境进行标准交付与运行：

### 2.1 快速部署三步走
```bash
cd /root/MaintainWise

# 1. 复制环境变量配置文件 (生产环境可按需微调数据库密码与 JWT 密钥)
cp .env.example .env

# 2. 执行自动化部署运维脚本
make deploy
# 或: bash deploy/scripts/deploy.sh

# 3. 访问与登录
# 浏览器访问: http://<服务器IP>
# 初始管理员账号: admin
# 初始管理员密码: MaintainWiseAdmin@2026
# (系统具备 SWR-USR-004 机制，首次登录将严格强制阻断并引导修改初始密码)
```

### 2.2 常用容器运维指令
```bash
make docker-up     # 编排拉起所有 5 大微服务容器
make docker-down   # 停止并销毁容器集群
make docker-logs   # 查看全集群实时日志流
make backup        # 执行全自动数据库与附件压缩备份
```

---

## 📋 3. 核心设计与 50 项需求实现追踪

- **SWR-USR-004 首次改密双重阻断**：后端依赖注入拦截器 [`check_fcp_status`](backend/app/api/deps.py)（错误码 `10008`）与前端全局路由守卫 [`guard.ts`](frontend/src/router/guard.ts)。
- **SWR-DEV-004 11 类设备专有参数强校验**：PLC 严格校验 IPv4 格式、风机风量风压大于零、三相电机绝缘等级等。
- **SWR-MNT-008 单事务巡检异常联锁提单**：现场巡检判定异常时，原子生成抢修单并将关联设备状态同步变更为 `FAULTY`。
- **SWR-FLT-005 故障并发抢单乐观锁**：单 SQL 条件原子更新解决多人并发抢单冲突，返回 `409 Conflict (40003)`。
- **SWR-KB-004 300ms 智能推荐与经验资产沉淀**：元数据过滤 + 文本加权双阶段打分推荐，故障复盘自动沉淀为知识条目。
- **SWR-NFR-005 车间现场平板触控适配**：$\ge 48\text{px}$ 垂直热区、大色块防误触单选卡片、拍照上传平滑锚定。

---

## 📚 4. 完整工程文档索引

所有架构设计与规范文档均已归档于 `docs/` 目录：

1. **[50项系统需求规范说明书 (SRS)](docs/system_requirements_specification.md)**
2. **[软件详细设计说明书 (SDD)](docs/software_detailed_design.md)**
3. **[Docker 部署与运维实战指南](docs/docker_deployment_guide.md)**
4. **[三轮工程反省与设计溯源报告](docs/requirements_reflection_audit.md)**
5. **[项目全量交付总报告](project_delivery_walkthrough.md)**
