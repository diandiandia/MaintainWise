.PHONY: help test test-backend test-frontend start deploy backup docker-up docker-down docker-logs clean

help:
	@echo "======================================================================"
	@echo "    MaintainWise 工业设备全生命周期维保协同系统 — 常用操作命令"
	@echo "======================================================================"
	@echo "【Linux 宿主机本地测试与开发】"
	@echo "  make start         : 一键启动 Linux 原生极速测试服务 (后端8000 + 前端3000)"
	@echo "  make test          : 运行 Linux 宿主机直接测试 (后端92项用例 + 前端构建)"
	@echo "  make test-backend  : 仅运行后端 Pytest 自动化测试套件"
	@echo "  make test-frontend : 仅运行前端 Vue 3 + TypeScript 检查与打包"
	@echo ""
	@echo "【Docker 容器集群生产运维】"
	@echo "  make deploy        : 执行一键 Docker 部署脚本"
	@echo "  make backup        : 执行数据库与附件全自动压缩备份"
	@echo "  make docker-up     : 编排启动所有 Docker 服务"
	@echo "  make docker-down   : 停止并清理 Docker 容器"
	@echo "  make docker-logs   : 查看容器实时聚合运行日志"
	@echo "======================================================================"

start:
	@bash deploy/scripts/start_local.sh

start-local:
	@bash deploy/scripts/start_local.sh

test:
	@bash deploy/scripts/test_local.sh

test-backend:
	@pytest -v backend/tests/

test-frontend:
	@npm run build --prefix frontend

deploy:
	@bash deploy/scripts/deploy.sh

backup:
	@bash deploy/scripts/backup.sh

docker-up:
	@docker compose up -d --build

docker-down:
	@docker compose down

docker-logs:
	@docker compose logs -f

clean:
	@rm -rf .pytest_cache frontend/dist frontend/node_modules/.vite maintainwise.db
