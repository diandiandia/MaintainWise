#!/bin/bash
# ==============================================================================
# MaintainWise — Linux 宿主机原生一键生产/测试部署运维脚本 (无需 Docker)
# 支持生命周期管理: install | start | stop | restart | status | logs | systemd
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

APP_PORT="${2:-8000}"
PID_FILE="$PROJECT_ROOT/maintainwise.pid"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/maintainwise.log"
VENV_DIR="$PROJECT_ROOT/.venv"

mkdir -p uploads "$LOG_DIR"

print_banner() {
    echo "======================================================================"
    echo "     MaintainWise 工厂设备维护管理系统 - Linux 原生一键部署运维工具     "
    echo "======================================================================"
}

get_python_bin() {
    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/python3" ] && [ -f "$VENV_DIR/bin/pip" ]; then
        echo "$VENV_DIR/bin/python3"
    elif [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/python" ] && [ -f "$VENV_DIR/bin/pip" ]; then
        echo "$VENV_DIR/bin/python"
    else
        which python3 2>/dev/null || echo "python3"
    fi
}

get_pip_bin() {
    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/pip" ]; then
        echo "$VENV_DIR/bin/pip"
    elif [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/pip3" ]; then
        echo "$VENV_DIR/bin/pip3"
    else
        which pip3 2>/dev/null || which pip 2>/dev/null || echo "pip"
    fi
}

# 1. 安装系统依赖并编译前端生产产物
do_install() {
    print_banner
    echo "📦 正在检测 Linux 基础环境并安装依赖..."

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ 错误: 未检测到 Python 3，请先安装 Python 3.10+ (如 apt install -y python3 python3-pip python3-venv)"
        exit 1
    fi
    echo "✅ 检测到 Python: $(python3 --version)"

    # 检查/配置 Python 虚拟环境 (针对 Ubuntu 24.04+/26.04+ 及 Debian 12+ PEP 668 externally-managed-environment 限制)
    echo "🐍 正在配置 Python 运行环境..."
    USE_VENV=false
    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/pip" ]; then
        USE_VENV=true
        echo "✅ 检测到已就绪的 Python 虚拟环境: $VENV_DIR"
    else
        rm -rf "$VENV_DIR"
        echo "   正在尝试创建独立虚拟环境: $VENV_DIR ..."
        if python3 -m venv "$VENV_DIR" 2>/dev/null && [ -f "$VENV_DIR/bin/pip" ]; then
            USE_VENV=true
            echo "✅ Python 独立虚拟环境创建成功: $VENV_DIR"
        else
            rm -rf "$VENV_DIR" # 立即清理残缺的虚拟环境目录，防止混淆 Python 解释器
            echo "ℹ️  未检测到完整 python3-venv 模块，将使用系统环境兼容模式。"
            echo "💡 提示: 若需使用标准隔离虚拟环境，可执行: sudo apt update && sudo apt install -y python3-venv"
        fi
    fi

    # 检查 Node.js 与 npm
    if ! command -v npm &> /dev/null; then
        echo "❌ 错误: 未检测到 npm，请先安装 Node.js 18+ (https://nodejs.org/)"
        exit 1
    fi
    echo "✅ 检测到 Node.js: $(node -v), npm: $(npm -v)"

    # 安装后端依赖
    echo "📥 1/3 正在安装后端 Python 依赖..."
    if [ "$USE_VENV" = true ] && [ -f "$VENV_DIR/bin/pip" ]; then
        echo "   使用虚拟环境 pip: $VENV_DIR/bin/pip"
        "$VENV_DIR/bin/pip" install --upgrade pip --quiet 2>/dev/null || true
        "$VENV_DIR/bin/pip" install -r backend/requirements.txt
    else
        echo "   使用系统 pip 安装 (兼容 PEP 668)..."
        pip3 install -r backend/requirements.txt --break-system-packages 2>/dev/null || \
        pip install -r backend/requirements.txt --break-system-packages 2>/dev/null || \
        pip3 install -r backend/requirements.txt --quiet || \
        pip install -r backend/requirements.txt --quiet
    fi

    # 安装前端依赖
    echo "📥 2/3 正在安装前端 Node.js 依赖..."
    npm --prefix frontend install --silent

    # 生产构建前端产物 (编译为 frontend/dist)
    echo "🔨 3/3 正在编译前端生产级静态资产..."
    npm run build --prefix frontend

    # 初始化数据库表结构与种子数据
    echo "🗄️ 正在初始化数据库结构与初始管理员账号..."
    PYTHON_EXEC=$(get_python_bin)
    PYTHONPATH=backend "$PYTHON_EXEC" backend/app/core/init_db.py

    echo "======================================================================"
    echo "🎉 MaintainWise 基础运行环境与前端生产构建已就绪！"
    echo "💡 您可以执行以下命令启动服务："
    echo "   bash deploy/scripts/deploy_linux.sh start [端口，默认8000]"
    echo "======================================================================"
}

# 2. 检查运行状态
get_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0 # Running
        fi
    fi
    return 1 # Not running
}

# 3. 启动后台服务
do_start() {
    print_banner
    if get_status; then
        echo "⚠️  MaintainWise 已经在运行中！(PID: $(cat "$PID_FILE"))"
        echo "🌐 访问地址: http://localhost:$APP_PORT 或 http://<服务器IP>:$APP_PORT"
        exit 0
    fi

    # 检查前端构建产物是否存在，若无则自动触发 build
    if [ ! -d "frontend/dist" ]; then
        echo "⚠️  检测到未构建前端生产资源，正在自动执行构建..."
        npm run build --prefix frontend
    fi

    PYTHON_EXEC=$(get_python_bin)
    echo "🚀 正在以后台常驻进程方式启动 MaintainWise (单端口直出 Web & API)..."
    echo "📌 服务监听端口: $APP_PORT"
    echo "📄 运行日志路径: $LOG_FILE"
    echo "🐍 运行时 Python: $PYTHON_EXEC"

    setsid "$PYTHON_EXEC" -m uvicorn app.main:app \
        --app-dir backend \
        --host 0.0.0.0 \
        --port "$APP_PORT" \
        > "$LOG_FILE" 2>&1 < /dev/null &
    
    PID=$!
    echo "$PID" > "$PID_FILE"

    # 等待探针就绪
    echo -n "⏳ 等待服务启动就绪"
    ATTEMPTS=0
    MAX_ATTEMPTS=15
    while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
        if curl -s "http://127.0.0.1:$APP_PORT/healthz" > /dev/null 2>&1; then
            break
        fi
        sleep 1
        ATTEMPTS=$((ATTEMPTS+1))
        echo -n "."
    done
    echo ""

    if curl -s "http://127.0.0.1:$APP_PORT/healthz" > /dev/null 2>&1; then
        echo "======================================================================"
        echo "🎉 MaintainWise 启动成功！(进程 PID: $PID)"
        echo "----------------------------------------------------------------------"
        echo "🌐 Web 访问地址    : http://<服务器IP>:$APP_PORT (单端口承载界面与API)"
        echo "📚 API 交互式文档  : http://<服务器IP>:$APP_PORT/api/v1/docs"
        echo "🔑 默认超级管理员  : admin"
        echo "🔒 默认初始密码    : MaintainWiseAdmin@2026"
        echo "⚠️  提示: 首次登录系统将强制要求修改初始密码！"
        echo "🛡️  防火墙配置说明  : 仅需在 Linux 服务器防火墙放行 $APP_PORT 端口"
        echo "======================================================================"
    else
        echo "❌ 服务启动异常，请查看日志排查问题："
        tail -n 20 "$LOG_FILE"
        exit 1
    fi
}

# 4. 停止服务
do_stop() {
    print_banner
    if ! get_status; then
        echo "ℹ️  MaintainWise 当前未在运行。"
        rm -f "$PID_FILE"
        return 0
    fi

    PID=$(cat "$PID_FILE")
    echo "🛑 正在停止 MaintainWise 进程 (PID: $PID)..."
    kill "$PID" 2>/dev/null || true

    # 等待优雅停止
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done

    # 若仍未退出则强制 kill
    if ps -p "$PID" > /dev/null 2>&1; then
        kill -9 "$PID" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    echo "✅ MaintainWise 服务已安全停止。"
}

# 5. 重启服务
do_restart() {
    do_stop
    sleep 1
    do_start
}

# 6. 查看服务状态
do_status() {
    print_banner
    if get_status; then
        PID=$(cat "$PID_FILE")
        echo "🟢 服务状态: 运行中 (Running)"
        echo "🆔 进程 PID: $PID"
        echo "📊 资源占用: $(ps -p "$PID" -o %cpu,%mem,cmd | tail -n 1)"
        echo "📄 最新日志:"
        tail -n 10 "$LOG_FILE" 2>/dev/null || echo "(无日志记录)"
    else
        echo "🔴 服务状态: 未运行 (Stopped)"
    fi
}

# 7. 实时查看日志
do_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "⚠️  日志文件 $LOG_FILE 尚不存在，服务可能尚未启动。"
        exit 1
    fi
    tail -f "$LOG_FILE"
}

# 8. 生成 systemd 开机自启服务配置
do_systemd() {
    print_banner
    SERVICE_FILE="/etc/systemd/system/maintainwise.service"
    CURRENT_USER=$(whoami)
    PYTHON_PATH=$(get_python_bin)

    echo "⚙️  正在生成 systemd 服务单元配置: $SERVICE_FILE"
    cat <<EOF | sudo tee "$SERVICE_FILE" > /dev/null
[Unit]
Description=MaintainWise Smart Factory Maintenance Management System
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_ROOT
ExecStart=$PYTHON_PATH -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $APP_PORT
Restart=always
RestartSec=5
Environment=RUN_MODE=linux_local
Environment=RUN_BACKGROUND_SCHEDULER=true

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    echo "✅ systemd 服务单元创建成功！"
    echo "💡 您可以使用以下命令管理开机自启系统服务："
    echo "   sudo systemctl enable maintainwise  # 设置开机自启"
    echo "   sudo systemctl start maintainwise   # 启动服务"
    echo "   sudo systemctl status maintainwise  # 查看状态"
    echo "   sudo systemctl restart maintainwise # 重启服务"
}

ACTION="${1:-start}"

case "$ACTION" in
    install)
        do_install
        ;;
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_restart
        ;;
    status)
        do_status
        ;;
    logs)
        do_logs
        ;;
    systemd)
        do_systemd
        ;;
    *)
        echo "用法: $0 {install|start|stop|restart|status|logs|systemd} [端口，默认8000]"
        exit 1
        ;;
esac
