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

## 3. 极速一键部署流程 (3步搞定)

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

