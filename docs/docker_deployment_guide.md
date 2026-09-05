# MaintainWise — Docker 容器化快速部署与运维指南

> **文档版本**：V1.0  
> **适用环境**：Linux (Ubuntu 20.04+, Debian 11+, CentOS 7.9+, RHEL 8+, Rocky Linux 9+)  
> **容器标准**：Docker 24.0+ / Docker Compose V2+  
> **最后更新**：2026-09-05

---

## 1. 部署架构概览

MaintainWise 采用标准全容器化微服务/模块化编排架构，通过 Docker Compose 实现单节点或集群化秒级一键交付：

```
                           外部网络 (Client / Tablet)
                                      │ HTTP:80 / HTTPS:443
                                      ▼
                        ┌───────────────────────────┐
                        │   maintainwise-gateway    │
                        │      (Nginx 1.25)         │
                        └─────────────┬─────────────┘
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            │ /                                                 │ /api/
            ▼                                                   ▼
┌───────────────────────────┐                       ┌───────────────────────────┐
│   maintainwise-frontend   │                       │    maintainwise-backend   │
│       (Vue 3 SPA)         │                       │      (FastAPI Engine)     │
└───────────────────────────┘                       └─────────────┬─────────────┘
                                                                  │
                                      ┌───────────────────────────┴──────────┐
                                      ▼                                      ▼
                        ┌───────────────────────────┐          ┌───────────────────────────┐
                        │   maintainwise-postgres   │          │    maintainwise-redis     │
                        │      (PostgreSQL 16)      │          │         (Redis 7)         │
                        │    [pg_trgm 全文检索]     │          │    [任务调度与防重锁]     │
                        └───────────────────────────┘          └───────────────────────────┘
```

---

## 2. 基础环境准备 (Linux)

若服务器尚未安装 Docker 与 Docker Compose，请参照对应系统的官方一键安装指令：

### Ubuntu / Debian
```bash
# 1. 卸载旧版本并更新基础源
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# 2. 官方一键脚本快速安装
curl -fsSL https://get.docker.com | bash -s docker

# 3. 启动并设置开机自启
sudo systemctl enable --now docker

# 4. 验证安装
docker --version
docker compose version
```

### CentOS / RHEL / Rocky Linux
```bash
# 1. 官方脚本安装
curl -fsSL https://get.docker.com | bash -s docker

# 2. 启动 Docker 服务
sudo systemctl enable --now docker

# 3. 验证安装
docker --version
docker compose version
```

---

## 3. Windows 电脑 Docker 环境搭建步骤 (Windows 10 / 11)

针对工程师在 Windows 笔记本或工控工位机（Windows 10 / Windows 11）上搭建 MaintainWise Docker 运行环境，请按以下标准化步骤操作：

### 3.1 硬件与系统前置要求
1. **操作系统版本**：
   - **Windows 11** 64 位（家庭版、专业版、企业版均可）；
   - 或 **Windows 10** 64 位（版本 2004 内部版本 19041 或更高版本）。
2. **CPU 虚拟化支持**：
   - 打开「任务管理器」(快捷键 `Ctrl + Shift + Esc`) $\rightarrow$ 切换至「性能」选项卡 $\rightarrow$ 点击「CPU」$\rightarrow$ 确认右下角显示 **“虚拟化：已启用”**。
   - 若显示“已禁用”，需在开机时进入电脑 BIOS/UEFI 设置（通常按 F2、F12 或 Del 键），开启 `Intel Virtual Technology (VT-x)` 或 `AMD SVM / SVM Mode`。

### 3.2 第一步：开启 Windows 虚拟化与 WSL 2 功能
以**管理员身份**打开 Windows PowerShell（在“开始”菜单搜索 PowerShell，右键点击“以管理员身份运行”），依次执行：

```powershell
# 1. 启用适用于 Linux 的 Windows 子系统 (WSL)
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# 2. 启用虚拟机平台功能
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 3. 更新并设定 WSL 默认版本为 2
wsl --update
wsl --set-default-version 2
```
> [!TIP]
> 执行完毕后，建议**重启一次 Windows 电脑**以使底层虚拟化内核组件完全生效。

### 3.3 第二步：下载与安装 Docker Desktop
1. 访问 Docker 官方下载页面：[https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)，下载 `Docker Desktop for Windows` 安装包。
2. 双击运行 `Docker Desktop Installer.exe`。
3. 在安装向导配置界面中，**务必确认勾选**：
   - ☑️ **Use WSL 2 instead of Hyper-V (recommended)**（采用 WSL 2 引擎，性能更高且家庭版原生支持）。
   - ☑️ **Add shortcut to desktop**（在桌面创建快捷方式）。
4. 安装完成后，点击 **Close and restart** 重启计算机完成最终注册。

### 3.4 第三步：Docker Desktop 优化与镜像加速配置
1. 在桌面上启动 **Docker Desktop**，接受服务条款（Accept）。
2. 点击右上角齿轮图标 ⚙️ **Settings** 进入设置面板：
   - **General**：确认已勾选 `Use the WSL 2 based engine`。
   - **Resources $\rightarrow$ WSL integration**：确认已开启默认 WSL 集成。
   - **Docker Engine**：为避免国内拉取 DockerHub 镜像因网络抖动超时，建议在 JSON 配置中增加国内镜像加速器及 DNS 配置：
     ```json
     {
       "builder": {
         "gc": {
           "defaultKeepStorage": "20GB",
           "enabled": true
         }
       },
       "experimental": false,
       "registry-mirrors": [
         "https://docker.m.daocloud.io",
         "https://huecker.io",
         "https://dockerhub.icu"
       ]
     }
     ```
   - 点击右下角 **“Apply & restart”** 保存并重启 Docker 引擎。
3. **验证环境就绪**：
   打开 PowerShell 或 CMD，输入以下命令验证：
   ```powershell
   docker --version
   docker compose version
   ```
   若正常输出版本号（如 `Docker version 27.x.x`、`Docker Compose version v2.x.x`），表明 Windows Docker 环境已完全搭建成功！

### 3.5 第四步：在 Windows 上一键运行 MaintainWise
1. 打开 PowerShell 进入 MaintainWise 所在目录（如 `D:\MaintainWise`）：
   ```powershell
   cd D:\MaintainWise
   ```
2. 复制生成环境配置文件：
   ```powershell
   Copy-Item .env.example .env
   ```
3. 一键构建并启动所有微服务集群：
   ```powershell
   docker compose up -d --build
   ```
4. 查看服务运行状态：
   ```powershell
   docker compose ps
   ```
   确认 `maintainwise-gateway`、`maintainwise-backend`、`maintainwise-frontend`、`maintainwise-postgres`、`maintainwise-redis` 均显示 `Up`。

### 3.6 Windows 局域网/内网访问与防火墙配置
若需要在同一工厂局域网内的其他工控机、车间工业平板或技术员电脑上访问该 Windows 宿主机上运行的 MaintainWise：
1. **查询本机内网 IP**：
   在 PowerShell 中运行 `ipconfig`，找到正在连接的以太网或 Wi-Fi 适配器的 `IPv4 地址`（如 `192.168.1.188`）。
2. **放行 Windows 防火墙入站 80 端口**：
   以管理员身份在 PowerShell 执行一条命令，放行 HTTP 80 端口入站访问：
   ```powershell
   New-NetFirewallRule -DisplayName "MaintainWise-HTTP-80" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow
   ```
3. **局域网设备接入**：
   车间平板或其他电脑在浏览器中输入 `http://192.168.1.188` 即可直接访问 MaintainWise 工业运维平台。

### 3.7 Windows 常见问题排查 (Troubleshooting)
- **Q1: 启动时提示 80 端口被占用 (`port is already allocated` 或 `listen tcp 0.0.0.0:80: bind: address already in use`)？**
  - **原因**：Windows 自带的 IIS 服务的 World Wide Web Publishing Service 占用了 80 端口。
  - **解决**：在管理员 PowerShell 中输入 `Stop-Service W3SVC` 并设为禁用，或者打开 `docker-compose.yml`，将 gateway 的端口映射修改为 `8080:80`，改用 `http://localhost:8080` 访问。
- **Q2: 提示 `WSL 2 installation is incomplete` 或内核版本过低？**
  - **解决**：运行 `wsl --update`，完成后运行 `wsl --shutdown`，再重新打开 Docker Desktop。
- **Q3: 提示 `Virtualization disabled in BIOS`？**
  - **解决**：进入电脑 BIOS 设置，找到 CPU 配置，开启 Intel VT-x 或 AMD SVM 虚拟化开关。

---

## 4. 极速一键部署流程 (Linux / 通用 3步搞定)

### 第一步：进入项目根目录
```bash
cd /root/MaintainWise
```

### 第二步：生成环境变量配置文件
系统已提供详尽注解的模板文件 [.env.example](file:///root/MaintainWise/.env.example)：
```bash
cp .env.example .env
```
*(可选) 使用文本编辑器微调密码及业务端口：*
```bash
nano .env   # 或 vim .env
```
> **提示**：生产环境建议修改 `POSTGRES_PASSWORD`、`REDIS_PASSWORD` 与 `SECRET_KEY`。

### 第三步：一键启动集群
直接执行部署运维脚本 [deploy.sh](file:///root/MaintainWise/deploy/scripts/deploy.sh)：
```bash
bash deploy/scripts/deploy.sh
```

或者使用原生 Docker Compose 命令直接启动：
```bash
docker compose up -d --build
```

---

## 4. 访问系统与初始凭证

服务构建并启动成功后，通过浏览器访问：
* **Web 访问地址**：`http://<您的服务器IP>` （默认 80 端口）
* **初始超级管理员账号**：`admin`
* **初始默认密码**：`MaintainWiseAdmin@2026`

> [!IMPORTANT]
> **安全改密约束 (REQ-USR-004)**：超级管理员首次登录系统后，系统将强制弹出改密界面，修改成功前所有业务操作被阻断。请在首次登录后立即设置符合规范的强密码。

---

## 5. 常用运维与管理命令速查

| 运维动作 | 命令行指令 |
|:---|:---|
| **查看集群容器运行状态** | `docker compose ps` |
| **查看所有服务实时滚动日志** | `docker compose logs -f` |
| **查看指定后端 API 日志** | `docker compose logs -f backend` |
| **停止所有服务** | `docker compose stop` |
| **启动所有服务** | `docker compose start` |
| **重启整个系统** | `docker compose restart` |
| **更新代码后平滑重新构建** | `docker compose up -d --build` |
| **进入 PostgreSQL 数据库命令行** | `docker exec -it maintainwise-postgres psql -U maintainwise -d maintainwise_db` |
| **进入 Redis 命令行** | `docker exec -it maintainwise-redis redis-cli -a MaintainWiseRedis2026` |

---

## 6. 数据持久化与自动化备份恢复

### 6.1 持久化数据卷清单
系统所有关键生产数据均通过 Docker 独立持久化卷或宿主机挂载目录保障安全，**容器销毁升级不会丢失任何数据**：
1. `maintainwise_pgdata`：PostgreSQL 核心数据库数据文件。
2. `maintainwise_redisdata`：Redis AOF 持久化日志。
3. `maintainwise_uploads`：现场拍摄的高清照片、故障证据、PDF 设备图纸与 PLC 程序备份。

### 6.2 自动化每日定时冷备 (Crontab)
项目已内置全自动备份与过期轮转清理脚本 [backup.sh](file:///root/MaintainWise/deploy/scripts/backup.sh)。

配置 Linux 系统定时任务（每天凌晨 02:00 自动执行备份，自动保留最近 30 天）：
```bash
# 编辑定时任务
crontab -e

# 添加如下一行：
0 2 * * * /bin/bash /root/MaintainWise/deploy/scripts/backup.sh >> /var/log/maintainwise_backup.log 2>&1
```

### 6.3 灾难恢复指南 (Restore)
若遇到极端服务器损坏，只需在新服务器启动新容器后执行恢复：
```bash
# 1. 解压恢复数据库 SQL
gunzip -c /root/MaintainWise/backups/maintainwise_db_YYYYMMDD_HHMMSS.sql.gz | \
docker exec -i maintainwise-postgres psql -U maintainwise -d maintainwise_db

# 2. 解压恢复工业图纸与现场照片
tar -xzf /root/MaintainWise/backups/maintainwise_uploads_YYYYMMDD_HHMMSS.tar.gz -C /root/MaintainWise/
```

---

## 7. 生产环境安全与 HTTPS SSL 加固

若工厂要求启用 `https://` 安全加密访问（端口 443）：

1. 将申请的企业 SSL 证书放置在 `/root/MaintainWise/deploy/nginx/ssl/` 目录下：
   * 证书公钥文件命名为：`server.crt`
   * 证书私钥文件命名为：`server.key`
2. 打开 [deploy/nginx/nginx.conf](file:///root/MaintainWise/deploy/nginx/nginx.conf)，解除 443 端口的 SSL 配置段注释。
3. 执行 `docker compose restart gateway` 即可无缝切换为 HTTPS。

---

## 8. 开发测试与生产部署双模运行规范 (Dual-Mode Specification)

MaintainWise 采用高度解耦的**双模运行体系**，明确区分「Linux 宿主机本地直接测试」与「Docker 容器化生产部署」：

### 8.1 运行模式与环境对照表

| 维度 | Linux 宿主机本地直接测试 (`linux_local`) | Docker 容器集群生产部署 (`docker_production`) |
|:---|:---|:---|
| **适用阶段** | 本地敏捷开发、CI 流水线、全量自动化测试 | 车间生产交付、云端集群部署、长时间稳定运行 |
| **基础设施要求** | 仅需基础 Python 3.10+ 与 Node 18+，**零外部依赖** | Docker Engine 24.0+ 与 Docker Compose V2+ |
| **数据库实现** | SQLite 本地轻量存储或内存库 (`maintainwise.db` / `:memory:`) | PostgreSQL 16 独立容器（持久化卷、启用 `pg_trgm` 向量全文检索） |
| **缓存与消息** | 本地内存 MockRedis 引擎（自动降级兜底） | Redis 7 独立容器（AOF 持久化、密码强保护） |
| **文件存储** | 动态解析当前项目根目录下的 `uploads/` | 容器映射目录 `/app/uploads`（Nginx 网关反代托管、50MB限制） |
| **后台定时任务** | 纯净按需调用，不开启守护循环，防止阻塞测试 | 自动拉起后台守护调度线程（巡检倒计时、SLA 告警、孤儿文件清理） |
| **执行命令** | `make test` 或 `bash deploy/scripts/test_local.sh` | `make deploy` 或 `bash deploy/scripts/deploy.sh` |

### 8.2 Linux 宿主机直接测试最佳实践
直接在 Linux 终端执行测试时，无需提前启动 Docker 服务，后端核心配置通过 `app/core/config.py` 自动计算相对路径并回退到零外部依赖模式：
```bash
# 1. 运行全量测试套件 (包含 28 个后端用例与前端生产打包)
make test

# 2. 仅运行指定专项测试
pytest -v backend/tests/test_e2e_integration.py
```

### 8.3 Docker 生产环境一键发布与交付
当代码在 Linux 宿主机通过所有测试用例后，交付部署只需一键拉起容器集群：
```bash
cp .env.example .env
make deploy
```

---
*(本文档为 MaintainWise 系统在工业车间现场快速投产交付与开发测试的标准操作手册)*

