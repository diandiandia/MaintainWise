# MaintainWise 工业设备维护管理系统 — 全场景部署与运维实战指南

> **文档版本**：V2.0  
> **适用环境**：Linux 全发行版 (Ubuntu 20.04+, Debian 11+, CentOS 7.9+, RHEL 8+, Rocky Linux 9+, AlmaLinux)  
> **支持架构**：x86_64 / aarch64 (ARM64)  
> **支持模式**：
> 1. **纯 Linux 宿主机原生一键部署**（轻量常驻、单端口全栈承载、零容器依赖）
> 2. **Docker 容器化微服务集群部署**（企业级生产交付、多容器编排、高可用网关）
> 3. **Linux 宿主机极速本地开发测试**（零配置前台直跑、双端热重载）

---

## 1. 部署架构与模式对比

MaintainWise 采用高度解耦的**多运行模式架构**，满足从单机轻量测试到工业车间高可用生产的全周期需求：

```
                    ┌───────────────────────────────────────────────┐
                    │               客户端访问流量                  │
                    │         (浏览器 / 工业平板触控终端)            │
                    └───────────────────────┬───────────────────────┘
                                            │
               ┌────────────────────────────┴────────────────────────────┐
               ▼                                                         ▼
┌─────────────────────────────┐                           ┌─────────────────────────────┐
│  模式 A: 纯 Linux 宿主机部署 │                           │   模式 B: Docker 容器集群   │
│   (deploy_linux.sh)         │                           │      (deploy.sh)            │
├─────────────────────────────┤                           ├─────────────────────────────┤
│ 1. 单端口直出 (默认 8000)   │                           │ 1. Nginx 统一网关 (80/443)  │
│ 2. FastAPI 托管 Vue 3 SPA   │                           │ 2. 前后端独立容器隔离       │
│ 3. 自动降级 SQLite/内存缓存 │                           │ 3. PostgreSQL 16 + Redis 7  │
│ 4. setsid/systemd 常驻守护  │                           │ 4. 数据卷隔离与全自动迁移   │
│ 5. 占用系统内存 ~100MB      │                           │ 5. 适合企业标准生产环境     │
└─────────────────────────────┘                           └─────────────────────────────┘
```

### 运行模式选择矩阵

| 评估维度 | 模式 A：Linux 宿主机原生部署 (`deploy_linux.sh`) | 模式 B：Docker 容器集群部署 (`deploy.sh`) | 模式 C：本地敏捷联调 (`start_local.sh`) |
| :--- | :--- | :--- | :--- |
| **启动命令** | `make deploy-linux` | `make deploy` | `make start` |
| **依赖要求** | Python 3.10+, Node.js 18+ | Docker 24.0+, Compose V2+ | Python 3.10+, Node.js 18+ |
| **对外开放端口** | **仅需 1 个端口**（`8000` 或 `80`） | **仅需 1 个端口**（`80`，可选 443） | **需 2 个端口**（`3000` + `8000`） |
| **数据存储** | 默认轻量 SQLite（可配 PG） | 独立 PostgreSQL 16 容器 | SQLite / 内存缓存 |
| **进程守护** | Linux `setsid` 守护或 `systemd` | Docker 容器生命周期守护 | 前台运行（Ctrl+C 退出） |
| **适用场景** | 快速验证、资源受限虚拟机、单机运行 | 团队生产环境、工厂车间落地、容器云 | 开发联调、本地单元与端到端测试 |

---

## 2. 端口规划与网络防火墙策略

### 2.1 端口使用明细

| 端口 | 协议 | 适用部署模式 | 作用与说明 | 对外暴露建议 |
| :--- | :--- | :--- | :--- | :--- |
| **`8000`** | TCP | 模式 A (原生部署) | **单端口承载全栈**：Web 前端 SPA 页面、REST API 及 Swagger 文档 | **必须放行**（若部署模式 A） |
| **`80`** | TCP | 模式 B (Docker 部署) | **Nginx 统一接入网关**：反向代理前端与 API | **必须放行**（若部署模式 B） |
| **`443`** | TCP | 模式 B (Docker 部署) | **HTTPS 安全加密网关**（可选） | 按需放行（需配置 SSL 证书） |
| **`3000`** | TCP | 模式 C (本地联调) | 前端 Vite 开发热重载服务器 | 仅本地或内部联调时放行 |
| **`5432`** | TCP | 模式 B (内部/外部) | PostgreSQL 16 数据库服务 | **生产环境禁止外网暴露** |
| **`6379`** | TCP | 模式 B (内部/外部) | Redis 7 高速缓存与任务队列 | **生产环境禁止外网暴露** |

### 2.2 防火墙与安全组配置实操

#### Ubuntu / Debian (UFW)
```bash
# 若采用模式 A (原生部署，默认 8000 端口):
sudo ufw allow 8000/tcp
sudo ufw reload

# 若采用模式 B (Docker 部署，80 端口):
sudo ufw allow 80/tcp
sudo ufw reload
```

#### CentOS / RHEL / Rocky Linux (Firewalld)
```bash
# 模式 A:
sudo firewall-cmd --zone=public --add-port=8000/tcp --permanent
sudo firewall-cmd --reload

# 模式 B:
sudo firewall-cmd --zone=public --add-port=80/tcp --permanent
sudo firewall-cmd --reload
```

#### 云服务器（阿里云 / 腾讯云 / 华为云 / AWS）
请登录云控制台，进入当前 ECS/CVM 实例的 **【安全组 (Security Group)】->【入方向规则】**，添加放行策略：
- **协议**：`TCP`
- **端口范围**：`8000`（或 `80`）
- **授权对象**：`0.0.0.0/0`（或企业内网网段）

---

## 3. 方案一：纯 Linux 宿主机原生一键部署实战

### 3.1 前置运行环境要求
- **操作系统**：Linux x86_64 或 ARM64
- **Python**：$\ge 3.10$（自带 `pip`）
- **Node.js**：$\ge 18.0$（自带 `npm`）

### 3.2 极速安装与部署步骤

#### 步骤 1：一键初始化与生产静态构建
在代码根目录执行：
```bash
bash deploy/scripts/deploy_linux.sh install
```
*该命令将自动安装后端 Python 依赖、安装前端 npm 依赖、编译生成 `frontend/dist` 生产资产，并初始化数据库结构与初始超级管理员账号。*

#### 步骤 2：启动后台常驻服务
```bash
# 方式 1：使用默认 8000 端口后台启动
make deploy-linux

# 方式 2：指定自定义端口（例如 80 端口）：
bash deploy/scripts/deploy_linux.sh start 80
```

#### 步骤 3：日常运维管理命令
```bash
make status-linux                         # 查看服务运行状态、PID 与 CPU/内存占用
bash deploy/scripts/deploy_linux.sh logs  # 实时查看系统运行日志
make stop-linux                           # 安全优雅停止服务
bash deploy/scripts/deploy_linux.sh restart 8000 # 平滑重启服务
```

#### 步骤 4：配置系统开机自启（可选但推荐）
如果希望服务器重启后系统自动拉起，可一键生成标准 `systemd` 服务：
```bash
bash deploy/scripts/deploy_linux.sh systemd 8000
```
生成后即可使用系统级标准指令管理：
```bash
sudo systemctl enable maintainwise  # 设置开机自启
sudo systemctl start maintainwise   # 启动服务
sudo systemctl status maintainwise  # 查看状态
```

---

## 4. 方案二：Docker 容器集群一键部署实战

### 4.1 前置运行环境要求
- **Docker Engine**：$\ge 24.0$
- **Docker Compose**：$\ge 2.0$

### 4.2 部署步骤

#### 步骤 1：配置文件与目录准备
```bash
# 1. 初始化生产环境变量配置
cp .env.example .env

# 2. 按需修改 .env 中的关键密钥与密码（生产环境建议变更）：
# POSTGRES_PASSWORD=YourStrongPassword2026!
# REDIS_PASSWORD=YourStrongRedisPassword2026!
# SECRET_KEY=your_production_unique_jwt_secret_key
```

#### 步骤 2：一键编排启动
```bash
make deploy
# 或直接执行部署脚本:
# bash deploy/scripts/deploy.sh
```
*脚本会自动校验环境、创建持久化卷、构建镜像、编排启动容器并等待健康探针就绪。*

#### 步骤 3：常用容器运维指令
```bash
make docker-logs   # 查看所有微服务聚合实时日志
docker compose ps  # 查看容器健康状态
make docker-down   # 优雅停止并清理容器
make backup        # 执行数据库与上传附件全量自动备份
```

---

## 5. 系统登录与初始设置指南

### 5.1 默认超级管理员登录
- **Web 访问入口**：
  - 纯 Linux 原生部署：`http://<服务器IP>:8000`
  - Docker 容器部署：`http://<服务器IP>` (80 端口)
- **默认用户名**：`admin`
- **默认初始密码**：`MaintainWiseAdmin@2026`

### 5.2 首次登录强制改密机制 (SWR-USR-004)
根据系统工业安全设计规范，超级管理员首次登录时，系统将阻断常规页面访问，强制弹出密码变更模态框：
- 新密码必须包含：**大写字母、小写字母、数字及特殊字符**，长度 $\ge 8$ 位；
- 成功修改密码后自动注销旧 Token，重新登录即可进入系统管理后台。

### 5.3 邮件服务器 (SMTP) 页面可视化配置 (SWR-SYS-001)
系统支持在 Web 管理界面对到期提醒邮件服务器进行免重启在线配置与测试：
1. 以超级管理员账号登录，进入侧边栏 **【系统设置】->【邮件服务器 (SMTP) 配置】**；
2. 填写企业邮件服务器信息：
   - **SMTP 主机**：如 `smtp.exmail.qq.com` 或 `smtp.office365.com`
   - **端口**：`465` (SSL) 或 `587` (TLS)
   - **账号与授权码**：发件人邮箱与 SMTP 密码/应用专用授权码
   - **发件人显示名称**：如 `MaintainWise 智能维保中心`
3. 点击 **【发送测试邮件】**，填写测试收件地址验证联通性；
4. 验证通过后点击 **【保存配置】**，系统将即时热重载配置，无需重启服务器或 Docker 容器。

---

## 6. 数据安全与灾备恢复

MaintainWise 提供全自动的一键压缩灾难备份脚本 [deploy/scripts/backup.sh](file:///root/MaintainWise/deploy/scripts/backup.sh)：

### 6.1 执行备份
```bash
make backup
# 或：bash deploy/scripts/backup.sh
```
* **备份产物**：保存在 `backups/` 目录下，包含以时间戳命名的 `maintainwise_backup_YYYYMMDD_HHMMSS.tar.gz`。
* **包含内容**：完整 PostgreSQL SQL 结构与数据转储、所有现场工单图片/SOP/培训附件目录 `uploads/`。
* **保留策略**：脚本自动清理超过 30 天的历史过期备份包。

### 6.2 灾难恢复
当遭遇服务器硬件故障或迁移新机时：
```bash
# 1. 解压备份包
tar -xzvf backups/maintainwise_backup_20260905_120000.tar.gz -C /tmp/restore/

# 2. 还原数据库 (以 Docker 环境为例)
docker exec -i maintainwise-postgres psql -U maintainwise -d maintainwise_db < /tmp/restore/db_dump.sql

# 3. 还原附件文件
cp -r /tmp/restore/uploads/* /root/MaintainWise/uploads/
```

---

## 7. 常见问题排查 (FAQ)

### Q1: 启动时提示端口被占用 (Address already in use: 8000 / 80)
- **排查命令**：`sudo lsof -i :8000` 或 `sudo netstat -tlpn | grep 8000`
- **解决方法**：
  1. 若为旧的 MaintainWise 进程，执行 `make stop-linux` 释放端口；
  2. 若端口被其他业务系统占用，在启动脚本中传入新端口，例如 `bash deploy/scripts/deploy_linux.sh start 8888`。

### Q2: 宿主机未安装 PostgreSQL 和 Redis，原生部署能正常运行吗？
- **完全可以**。系统内置零配置降级引擎：未配置外置数据库时自动切换为持久化 SQLite，未安装物理 Redis 时自动启用内存 MockRedis 引擎，全部 50 项业务功能均正常运转。

### Q3: 访问 Web 页面提示 404 或静态资源加载失败？
- 请确认是否已执行前端生产构建。执行 `bash deploy/scripts/deploy_linux.sh install` 重新编译出 `frontend/dist` 静态资源目录即可。
