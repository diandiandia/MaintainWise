#!/bin/bash
# ==============================================================================
# MaintainWise — 数据自动定时备份脚本 (PostgreSQL + 附件文件)
# 推荐添加到 crontab 每日凌晨 02:00 执行:
# 0 2 * * * /root/MaintainWise/deploy/scripts/backup.sh >> /var/log/maintainwise_backup.log 2>&1
# ==============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=30

mkdir -p "${BACKUP_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始执行 MaintainWise 系统全量数据冷备..."

# 1. 备份 PostgreSQL 数据库
DB_BACKUP_FILE="${BACKUP_DIR}/maintainwise_db_${TIMESTAMP}.sql.gz"
echo "正在导出数据库至 ${DB_BACKUP_FILE} ..."
docker exec maintainwise-postgres pg_dump -U maintainwise -d maintainwise_db | gzip > "${DB_BACKUP_FILE}"
echo "✅ 数据库备份完成，文件大小: $(du -h "${DB_BACKUP_FILE}" | cut -f1)"

# 2. 备份工业图纸、照片与程序附件
UPLOADS_BACKUP_FILE="${BACKUP_DIR}/maintainwise_uploads_${TIMESTAMP}.tar.gz"
echo "正在归档附件目录至 ${UPLOADS_BACKUP_FILE} ..."
tar -czf "${UPLOADS_BACKUP_FILE}" -C "${PROJECT_ROOT}" uploads
echo "✅ 附件文件备份完成，文件大小: $(du -h "${UPLOADS_BACKUP_FILE}" | cut -f1)"

# 3. 清理超过 30 天的历史过期备份
echo "正在清理 ${RETENTION_DAYS} 天前的过期备份..."
find "${BACKUP_DIR}" -type f -name "maintainwise_*" -mtime +${RETENTION_DAYS} -exec rm -f {} \;

echo "[$(date '+%Y-%m-%d %H:%M:%S')] MaintainWise 全量数据备份顺利完成！"
