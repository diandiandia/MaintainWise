#!/bin/bash
# ==============================================================================
# MaintainWise — Linux 宿主机原生极速测试启动脚本 (零依赖模式)
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo "    正在启动 MaintainWise Linux 原生极速测试环境 (无需 Docker/DB)"
echo "======================================================================"

# 1. 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未检测到 Python 3，请先安装 Python 3.10+"
    exit 1
fi

# 2. 检查 Node.js / npm
if ! command -v npm &> /dev/null; then
    echo "❌ 错误: 未检测到 npm / Node.js，请先安装 Node.js 18+"
    exit 1
fi

# 3. 准备运行目录
mkdir -p uploads

# 优雅退出信号捕获
cleanup() {
    echo ""
    echo "🛑 正在停止所有本地测试服务进程..."
    kill $(jobs -p) 2>/dev/null || true
    echo "✅ 服务已安全关闭。"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "🚀 1. 正在启动后端 FastAPI 服务 (端口 8000, 自动启用 SQLite 与内存缓存)..."
python3 -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 等待后端就绪
sleep 2

echo "🚀 2. 正在启动前端 Vite 界面服务 (端口 3000)..."
echo "======================================================================"
echo "🎉 MaintainWise 本地原生测试环境已启动成功！"
echo "----------------------------------------------------------------------"
echo "🌐 前端 Web 访问地址  : http://localhost:3000 或 http://<服务器IP>:3000"
echo "📚 交互式 API 文档   : http://localhost:8000/api/v1/docs"
echo "🔑 默认超级管理员    : admin"
echo "🔒 默认初始密码      : MaintainWiseAdmin@2026"
echo "⚠️  需要开放的防火墙端口: 3000 (前端界面) 和 8000 (后端API)"
echo "----------------------------------------------------------------------"
echo "💡 按 Ctrl+C 可停止当前服务集群"
echo "======================================================================"

npm run dev --prefix frontend -- --host 0.0.0.0 --port 3000
