# MaintainWise 工业设备全生命周期维保协同系统

> **面向离散制造业的现代化设备健康管理、预防性维保、突发抢修协同与经验资产沉淀平台。**  
> 基于 **FastAPI + SQLAlchemy 2.0 + PostgreSQL 16 + Redis 7** 后端架构与 **Vue 3 + TypeScript + Element Plus + ECharts** 工控触控前端构建。

---

## 🚀 两种运行环境与定位 (Dual-Mode Architecture)

MaintainWise 采用高度解耦的**双模运行体系**，完美支持「Docker 容器集群自动化生产交付」与「Linux 宿主机原生一键生产/测试运行」：

| 维度 | 方案 A：Docker 容器集群一键生产部署 (`docker_production`) | 方案 B：Linux 宿主机原生一键常驻部署 (`linux_native`) |
|:---|:---|:---|
| **核心定位** | 工厂生产环境交付、微服务集群编排、标准全隔离运行 | 传统 Linux 服务器、无 Docker 环境、轻量低配工控机 |
| **外部依赖要求** | **Docker 24.0+ & Docker Compose V2+** | **Python 3.10+ & Node.js 18+** (一键脚本全自动安装) |
| **持久化数据库** | 独立容器 PostgreSQL 16 (挂载持久卷，`pg_trgm` 全文检索) | 本地 SQLite 高性能文件数据库 (`maintainwise.db`) 自动托管 |
| **高速缓存与队列**| 独立容器 Redis 7 (启用 AOF 持久化与连接池) | 本地内存 MockRedis 高效运行引擎自动降级 |
| **Web 网关与端口** | Nginx 反向代理网关，对外统一暴露 **HTTP:80** / HTTPS:443 | FastAPI 原生聚合全栈服务，对外暴露 **HTTP:8000** |
| **一键部署指令** | `bash deploy/scripts/deploy.sh` 或 `make deploy` | `bash deploy/scripts/deploy_linux.sh install && start` |

---

## ⚡ 极速一键部署指南 (One-Click Deployment)

系统已内置自动化运维部署脚本，**一键即可完成所有构建、配置生成、数据库初始化与后台常驻启动**：

### 🐳 方式一：Docker 容器集群一键部署 (生产首选，支持 Linux & Windows)

适用于车间主服务器、云服务器或安装了 Docker 的工控机：

#### 1. Linux 服务器一键部署
```bash
cd /root/MaintainWise

# 执行一键部署脚本 (自动生成 .env、编译镜像、编排拉起 5 大微服务并自检)
bash deploy/scripts/deploy.sh

# 或者使用 Makefile 快捷命令:
# make deploy
```

#### 2. 🪟 Windows 电脑 (Windows 10 / 11) 一键部署
在 Windows 笔记本或台式工控机上，通过 **WSL 2 + Docker Desktop** 极速运行：
```powershell
# 1. 打开 PowerShell 进入项目目录
cd D:\MaintainWise

# 2. 生成配置文件
Copy-Item .env.example .env

# 3. 一键构建并启动所有容器
docker compose up -d --build
```
> [!TIP]
> **详细步骤指引**：关于 Windows 开启 WSL 2、安装 Docker Desktop、配置国内镜像加速与放行 Windows 防火墙入站 80 端口，详见完整文档：[Docker 容器化快速部署与运维指南](docs/docker_deployment_guide.md#3-windows-电脑-docker-环境搭建步骤-windows-10--11)。

#### 3. Docker 常用运维命令
```bash
make docker-up     # 启动/更新所有容器集群
make docker-down   # 停止并清理容器集群
make docker-logs   # 查看全集群实时聚合滚动日志
make backup        # 执行数据库与附件压缩冷备份
```

---

### 🐧 方式二：Linux 原生裸机一键部署 (无需安装 Docker)

适用于不具备 Docker 环境、不想运行容器的 Linux 宿主机（Ubuntu 20.04+ / Debian 11+ / CentOS 7.9+ / Rocky Linux 9+）：

#### 1. 一键安装基础依赖与编译前端产物
```bash
cd /root/MaintainWise

# 自动检测 Python、配置隔离虚拟环境、安装依赖、编译 Vue 3 前端静态产物
bash deploy/scripts/deploy_linux.sh install
```

#### 2. 一键以后台守护进程方式常驻启动
```bash
# 以后台守护进程方式启动 (默认 8000 端口，单个端口同时提供前端页面与后端 API)
bash deploy/scripts/deploy_linux.sh start 8000

# 或者使用 Makefile:
# make deploy-linux
```

#### 3. 运维生命周期管理指令
```bash
bash deploy/scripts/deploy_linux.sh status   # 查看当前运行状态与进程 PID (或 make status-linux)
bash deploy/scripts/deploy_linux.sh logs     # 实时滚动查看系统运行日志
bash deploy/scripts/deploy_linux.sh restart  # 一键平滑重启服务
bash deploy/scripts/deploy_linux.sh stop     # 优雅停止后台服务 (或 make stop-linux)
bash deploy/scripts/deploy_linux.sh systemd  # 生成 systemd 系统服务，实现开机自动拉起
```

---

### 🛠️ 方式三：本地开发与自动化全量测试
```bash
# 一键执行全量自动化测试套件 (包含后端 93 项业务规范测试 + 前端 TypeScript 打包编译)
make test
# 或: bash deploy/scripts/test_local.sh

# 仅运行后端 Pytest 测试
make test-backend

# 仅运行前端 Vue 3 + TypeScript 检查与打包
make test-frontend
```

---

## 🔑 系统访问与初始凭据

服务启动后，通过浏览器即可访问工业运维平台：

* **Web 访问地址**：
  * **Docker 部署**：`http://<您的服务器IP>` （默认 80 端口）或 `http://localhost`
  * **Linux 原生部署**：`http://<您的服务器IP>:8000`
* **默认超级管理员账号**：`admin`
* **默认初始强密码**：`MaintainWiseAdmin@2026`

> [!IMPORTANT]
> **安全改密强拦截 (SWR-USR-004)**：超级管理员首次登录系统后，系统将强制弹出改密对话框，成功修改密码前所有业务操作与接口均被严格阻断，保障出厂生产安全。

---

## 🌐 局域网 (内网) 互联访问与防火墙配置

MaintainWise 原生支持车间同一局域网内的工位电脑、工业平板和移动终端互通：

1. **查询宿主机内网 IP**：
   - Linux: 执行 `hostname -I` 或 `ip addr`（如 `192.168.1.188`）。
   - Windows: PowerShell 执行 `ipconfig` 查询 IPv4 地址。
2. **防火墙放行端口**：
   - **Linux (UFW)**：`sudo ufw allow 80/tcp` (Docker) 或 `sudo ufw allow 8000/tcp` (原生)。
   - **Linux (Firewalld)**：`sudo firewall-cmd --permanent --add-port=80/tcp && sudo firewall-cmd --reload`。
   - **Windows PowerShell (管理员)**：
     ```powershell
     New-NetFirewallRule -DisplayName "MaintainWise-HTTP-80" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow
     ```
3. **现场设备接入**：现场平板或技术员在浏览器输入 `http://192.168.1.188` 即可流畅操作。

---

## 📋 3. 核心设计与 50 项需求实现追踪

- **SWR-DEV-001 4 级层级拓扑树 (工厂 $\rightarrow$ 部门 $\rightarrow$ 系统 $\rightarrow$ 设备信息)**：管理员统筹录入并管理 4 级拓扑结构，设备信息标准化挂载。
- **SWR-USR-001/002 三大标准工业角色与免工种数据隔离**：精简内置 `ADMIN`、`ENGINEER`、`TECHNICIAN` 三大角色（不设车间主管），彻底取消责任工种数据隔离，消除工种壁垒与信息孤岛。
- **SWR-MNT-001/004 小时级设备维护计划与精确倒计时**：编制设备维护计划内部倒计时周期单位最小为**小时**，后台小时级动态扫描并精准计算到期时刻。
- **SWR-MNT-007 现场维护单、工单编辑与工作完成证据**：技术员接单后，具备**编辑工单信息**及**上传现场图片作为工作完成证据**功能。
- **SWR-MNT-008 单事务现场维护异常联锁提单**：现场维护判定异常时，原子生成抢修单并将关联设备状态同步变更为 `FAULTY`。
- **SWR-DSH-001 数据平台 (FCM设备运维管理平台)**：集中呈现设备健康状态、倒计时指标与维保统计。
- **SWR-FLT-005 故障并发抢单乐观锁**：单 SQL 条件原子更新解决多人并发抢单冲突，返回 `409 Conflict (40003)`。
- **SWR-KB-004 300ms 智能推荐与经验资产沉淀**：元数据过滤 + 文本加权双阶段打分推荐，故障复盘自动沉淀为知识条目。
- **SWR-NFR-005 车间现场平板触控适配**：$\ge 48\text{px}$ 垂直热区、大色块防误触单选卡片、拍照上传平滑锚定。

---

## 📚 4. 完整工程文档索引

所有架构设计与规范文档均已归档于 `docs/` 目录：

1. **[业务需求规格说明书 V1.0 (PRD)](docs/requirements_V1.md)**
2. **[系统需求规格说明书 (SRS)](docs/system_requirements_specification.md)**
3. **[软件需求规格说明书 (Software SRS)](docs/software_requirements_specification.md)**
4. **[系统架构与概要设计说明书 (SDD)](docs/system_design_document.md)**
5. **[软件详细设计说明书 (Detailed SDD)](docs/software_detailed_design.md)**
6. **[全场景部署与运维实战指南 (Linux/Docker)](docs/system_deployment_guide.md)**
7. **[Docker 容器化专项部署指南](docs/docker_deployment_guide.md)**
8. **[工程反省与设计溯源报告](docs/requirements_reflection_audit.md)**
