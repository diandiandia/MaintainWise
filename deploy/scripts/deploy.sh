#!/bin/bash
# ==============================================================================
# MaintainWise — 一键 Docker 快速部署运维脚本
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo "    正在启动 MaintainWise 工厂设备维护管理系统 一键部署..."
echo "======================================================================"

# 1. 检查 Docker 及 Docker Compose 环境
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: 未检测到 Docker，请先安装 Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ 错误: 未检测到 Docker Compose 插件，请先安装 docker compose"
    exit 1
fi

# 2. 检查环境变量配置 .env
if [ ! -f .env ]; then
    echo "⚠️  未发现 .env 配置文件，正在从 .env.example 自动生成..."
    cp .env.example .env
    echo "✅ .env 文件已初始化，请在需要时手动修改密码与密钥配置。"
fi

# 3. 创建持久化数据与附件目录
mkdir -p uploads deploy/nginx/ssl

# 4. 构建并启动所有容器服务
echo "🚀 正在拉取依赖并编排启动服务集群 (PostgreSQL, Redis, Backend, Frontend, Nginx)..."
docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d --build

# 5. 等待网关与服务就绪
echo "⏳ 正在等待核心服务健康就绪..."
ATTEMPTS=0
MAX_ATTEMPTS=30
until curl -s http://localhost/healthz > /dev/null 2>&1 || [ $ATTEMPTS -eq $MAX_ATTEMPTS ]; do
    sleep 2
    ATTEMPTS=$((ATTEMPTS+1))
    echo -n "."
done
echo ""

if [ $ATTEMPTS -eq $MAX_ATTEMPTS ]; then
    echo "⚠️  服务启动超时，请使用 'docker compose logs' 检查容器日志。"
else
    echo "======================================================================"
    echo "🎉 MaintainWise 部署成功！"
    echo "----------------------------------------------------------------------"
    echo "🌐 Web 访问地址    : http://<服务器IP> 或 http://localhost"
    echo "🔑 默认超级管理员  : admin"
    echo "🔒 默认初始密码    : MaintainWiseAdmin@2026"
    echo "⚠️  提示: 首次登录系统将强制要求修改初始密码！"
    echo "📊 容器状态检查    : docker compose ps"
    echo "📜 查看实时运行日志: docker compose logs -f"
    echo "======================================================================"
fi
