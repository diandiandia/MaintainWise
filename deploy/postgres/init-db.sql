-- ==============================================================================
-- MaintainWise — PostgreSQL 数据库初始结构与种子数据脚本 (V1.0)
-- ==============================================================================

-- 1. 启用扩展支持 (全文模糊匹配与UUID)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. 系统用户表 (sys_users)
CREATE TABLE IF NOT EXISTS sys_users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(64) NOT NULL,
    employee_no VARCHAR(32) NOT NULL UNIQUE,
    email VARCHAR(128) NOT NULL,
    phone VARCHAR(32),
    role_code VARCHAR(32) NOT NULL, -- 'ADMIN', 'ENGINEER', 'TECHNICIAN'
    work_type VARCHAR(32) NOT NULL, -- 'ELECTRICAL', 'MECHANICAL', 'AUTOMATION', 'GENERAL'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    force_change_password BOOLEAN NOT NULL DEFAULT TRUE,
    password_updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by BIGINT,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 3. 系统只读审计日志表 (sys_audit_logs)
CREATE TABLE IF NOT EXISTS sys_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    username VARCHAR(64),
    client_ip VARCHAR(45) NOT NULL,
    module_name VARCHAR(64) NOT NULL,
    action_type VARCHAR(32) NOT NULL, -- 'CREATE', 'UPDATE', 'DELETE', 'EXPORT'
    request_url VARCHAR(255) NOT NULL,
    request_method VARCHAR(10) NOT NULL,
    diff_payload JSONB,
    status_code INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON sys_audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_module ON sys_audit_logs(module_name, action_type);

-- 4. 车间层级拓扑树位置表 (equipment_locations: 工厂->部门->系统)
CREATE TABLE IF NOT EXISTS equipment_locations (
    id BIGSERIAL PRIMARY KEY,
    parent_id BIGINT REFERENCES equipment_locations(id) ON DELETE RESTRICT,
    location_name VARCHAR(128) NOT NULL,
    location_code VARCHAR(64) NOT NULL UNIQUE,
    level_depth INT NOT NULL CHECK (level_depth BETWEEN 1 AND 5),
    node_type VARCHAR(32) NOT NULL DEFAULT 'SYSTEM', -- 'FACTORY', 'DEPARTMENT', 'SYSTEM'
    tree_path VARCHAR(255) NOT NULL,
    is_leaf BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by BIGINT,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_loc_parent ON equipment_locations(parent_id);
CREATE INDEX IF NOT EXISTS idx_loc_path ON equipment_locations(tree_path);

-- 5. 设备台账主表 (equipments: 第4级设备信息挂载)
CREATE TABLE IF NOT EXISTS equipments (
    id BIGSERIAL PRIMARY KEY,
    equipment_code VARCHAR(64) NOT NULL UNIQUE,
    equipment_name VARCHAR(128) NOT NULL,
    equipment_type VARCHAR(32) DEFAULT 'GENERAL', -- 缺省通用设备
    work_type VARCHAR(32) DEFAULT 'GENERAL', -- 缺省通用专业
    location_id BIGINT NOT NULL REFERENCES equipment_locations(id) ON DELETE RESTRICT,
    manufacturer VARCHAR(128),
    model_spec VARCHAR(128) NOT NULL,
    serial_number VARCHAR(128),
    rated_voltage VARCHAR(64),
    params_text TEXT, -- 设备参数信息自由文本
    purchase_date DATE,
    commission_date DATE,
    warranty_expiry_date DATE,
    maintenance_interval_days INT NOT NULL DEFAULT 30,
    maintenance_interval_hours INT NOT NULL DEFAULT 720, -- 倒计时周期最小为小时
    next_maintenance_date DATE,
    responsible_engineer_id BIGINT REFERENCES sys_users(id),
    status VARCHAR(32) NOT NULL DEFAULT 'RUNNING', -- RUNNING, MAINTENANCE_PENDING, FAULTY, SHUTDOWN, SCRAPPED
    current_operating_hours NUMERIC(10, 2) NOT NULL DEFAULT 0.0, -- 当前维保周期已累计运行工时
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT REFERENCES sys_users(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by BIGINT REFERENCES sys_users(id),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_eq_code_name ON equipments(equipment_code, equipment_name);
CREATE INDEX IF NOT EXISTS idx_eq_type_work ON equipments(equipment_type, work_type);
CREATE INDEX IF NOT EXISTS idx_eq_status ON equipments(status);
CREATE INDEX IF NOT EXISTS idx_eq_next_maint ON equipments(next_maintenance_date);

-- 6. 设备专有参数扩展表 (equipment_params)
CREATE TABLE IF NOT EXISTS equipment_params (
    equipment_id BIGINT PRIMARY KEY REFERENCES equipments(id) ON DELETE CASCADE,
    rated_power_kw NUMERIC(10, 2),
    rated_voltage_v NUMERIC(10, 2),
    rated_current_a NUMERIC(10, 2),
    rated_speed_rpm INT,
    air_volume_m3h NUMERIC(10, 2),
    air_pressure_pa NUMERIC(10, 2),
    ip_address VARCHAR(45),
    comm_protocol VARCHAR(64),
    io_points_spec VARCHAR(128),
    pressure_range_mpa NUMERIC(10, 2),
    measurement_range VARCHAR(64),
    output_signal_type VARCHAR(64),
    accuracy_class VARCHAR(32),
    extra_params JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- 7. 附件文件表 (equipment_files)
CREATE TABLE IF NOT EXISTS equipment_files (
    id BIGSERIAL PRIMARY KEY,
    equipment_id BIGINT REFERENCES equipments(id) ON DELETE SET NULL,
    file_tag VARCHAR(32) NOT NULL, -- PHOTO, NAMEPLATE, MANUAL, SCHEMATIC, PLC_PROG, FAULT_IMG, OTHER
    original_filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(512) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    file_sha256 VARCHAR(64) NOT NULL,
    is_linked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT REFERENCES sys_users(id)
);
CREATE INDEX IF NOT EXISTS idx_files_eq_tag ON equipment_files(equipment_id, file_tag);
CREATE INDEX IF NOT EXISTS idx_files_is_linked ON equipment_files(is_linked);

-- 7.1 设备运行工时填报与流水表 (equipment_operating_logs) (SWR-MNT-012)
CREATE TABLE IF NOT EXISTS equipment_operating_logs (
    id BIGSERIAL PRIMARY KEY,
    equipment_id BIGINT NOT NULL REFERENCES equipments(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    duration_hours NUMERIC(10, 2) NOT NULL,
    cumulative_hours NUMERIC(10, 2) NOT NULL,
    proof_image_id BIGINT REFERENCES equipment_files(id),
    operator_id BIGINT NOT NULL REFERENCES sys_users(id),
    remarks VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_op_logs_eq_date ON equipment_operating_logs(equipment_id, log_date);

-- 8. 维护计划与 SOP 表 (maintenance_plans)
CREATE TABLE IF NOT EXISTS maintenance_plans (
    id BIGSERIAL PRIMARY KEY,
    plan_code VARCHAR(64) NOT NULL UNIQUE,
    plan_name VARCHAR(128) NOT NULL,
    plan_type VARCHAR(32) NOT NULL, -- DAILY, WEEKLY, MONTHLY, ANNUAL, HOURLY
    trigger_mode VARCHAR(32) NOT NULL DEFAULT 'CALENDAR', -- CALENDAR (日历天) / OPERATING_HOURS (工时制)
    interval_days INT NOT NULL DEFAULT 30,
    interval_hours INT NOT NULL DEFAULT 720, -- 倒计时周期最小为小时
    advance_notice_days INT NOT NULL DEFAULT 3, -- 提前预警天数 (日历周期模式)
    advance_warning_hours INT NOT NULL DEFAULT 48, -- 提前预警小时数 (工时模式默认提前48小时通知)
    version_no VARCHAR(16) NOT NULL DEFAULT 'V1.0',
    sop_content TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    equipment_ids JSONB NOT NULL DEFAULT '[]', -- 关联设备ID列表，支持多设备共用同一维护计划
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT REFERENCES sys_users(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by BIGINT REFERENCES sys_users(id),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 9. 维护检查清单配置表 (maintenance_plan_items)
CREATE TABLE IF NOT EXISTS maintenance_plan_items (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES maintenance_plans(id) ON DELETE CASCADE,
    item_order INT NOT NULL DEFAULT 1,
    check_item_name VARCHAR(128) NOT NULL,
    standard_benchmark TEXT NOT NULL,
    guide_image_id BIGINT REFERENCES equipment_files(id),
    is_required BOOLEAN NOT NULL DEFAULT TRUE
);

-- 10. 维护待办调度工单表 (maintenance_tasks)
CREATE TABLE IF NOT EXISTS maintenance_tasks (
    id BIGSERIAL PRIMARY KEY,
    task_code VARCHAR(64) NOT NULL UNIQUE,
    plan_id BIGINT NOT NULL REFERENCES maintenance_plans(id),
    equipment_id BIGINT NOT NULL REFERENCES equipments(id),
    assigned_tech_id BIGINT REFERENCES sys_users(id),
    plan_version_snapshot VARCHAR(16) NOT NULL,
    scheduled_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- PENDING, IN_PROGRESS, COMPLETED, OVERDUE
    completed_at TIMESTAMP,
    claimed_at TIMESTAMP, -- 技术员接单时间
    work_order_notes TEXT, -- 技术员作业执行与编辑说明
    completion_proof_file_ids JSONB NOT NULL DEFAULT '[]', -- 现场工作完成证据图片文件ID列表
    is_overdue BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tasks_eq_due ON maintenance_tasks(equipment_id, due_date, status);

-- 11. 巡检打卡执行总表 (inspection_records)
CREATE TABLE IF NOT EXISTS inspection_records (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT REFERENCES maintenance_tasks(id),
    equipment_id BIGINT NOT NULL REFERENCES equipments(id),
    snapshot_location_id BIGINT NOT NULL REFERENCES equipment_locations(id),
    inspector_id BIGINT NOT NULL REFERENCES sys_users(id),
    has_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    execution_start_time TIMESTAMP NOT NULL,
    execution_end_time TIMESTAMP NOT NULL DEFAULT NOW(),
    overall_remarks TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 12. 逐项巡检打卡明细表 (inspection_record_details)
CREATE TABLE IF NOT EXISTS inspection_record_details (
    id BIGSERIAL PRIMARY KEY,
    record_id BIGINT NOT NULL REFERENCES inspection_records(id) ON DELETE CASCADE,
    plan_item_id BIGINT NOT NULL,
    check_item_name_snapshot VARCHAR(128) NOT NULL,
    is_normal BOOLEAN NOT NULL,
    anomaly_desc TEXT,
    evidence_file_id BIGINT REFERENCES equipment_files(id),
    interlocked_fault_id BIGINT
);

-- 13. 故障全流程跟踪表 (fault_records)
CREATE TABLE IF NOT EXISTS fault_records (
    id BIGSERIAL PRIMARY KEY,
    fault_code VARCHAR(64) NOT NULL UNIQUE,
    source_type VARCHAR(32) NOT NULL, -- 'INSPECTION_AUTO', 'MANUAL_REPORT'
    equipment_id BIGINT NOT NULL REFERENCES equipments(id),
    snapshot_location_id BIGINT NOT NULL REFERENCES equipment_locations(id),
    fault_title VARCHAR(128) NOT NULL,
    fault_desc TEXT NOT NULL,
    fault_system VARCHAR(64) NOT NULL,
    fault_part VARCHAR(128) NOT NULL,
    severity_level VARCHAR(32) NOT NULL, -- 'CRITICAL', 'MAJOR', 'MINOR'
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN', -- OPEN, IN_PROGRESS, RESOLVED_PENDING_REVIEW, RESOLVED, CLOSED, REOPENED
    reported_by BIGINT NOT NULL REFERENCES sys_users(id),
    reported_at TIMESTAMP NOT NULL DEFAULT NOW(),
    assigned_engineer_id BIGINT REFERENCES sys_users(id),
    claimed_at TIMESTAMP,
    root_cause TEXT,
    solution_steps TEXT,
    downtime_minutes INT DEFAULT 0,
    is_featured_case BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at TIMESTAMP,
    closed_at TIMESTAMP,
    is_sla_response_breached BOOLEAN NOT NULL DEFAULT FALSE,
    is_sla_resolve_breached BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT REFERENCES sys_users(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by BIGINT REFERENCES sys_users(id),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_fault_status_sev ON fault_records(status, severity_level);
CREATE INDEX IF NOT EXISTS idx_fault_eq_rep ON fault_records(equipment_id, reported_at);

-- 14. 维修知识库全文检索表 (knowledge_articles)
CREATE TABLE IF NOT EXISTS knowledge_articles (
    id BIGSERIAL PRIMARY KEY,
    article_code VARCHAR(64) NOT NULL UNIQUE,
    source_fault_id BIGINT REFERENCES fault_records(id) ON DELETE SET NULL,
    equipment_type VARCHAR(32) NOT NULL,
    equipment_model VARCHAR(128) NOT NULL,
    fault_system VARCHAR(64) NOT NULL,
    fault_title VARCHAR(128) NOT NULL,
    fault_phenomenon TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    solution_steps TEXT NOT NULL,
    tags VARCHAR(255)[],
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,
    view_count INT NOT NULL DEFAULT 0,
    helpful_count INT NOT NULL DEFAULT 0,
    search_vector TSVECTOR,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT REFERENCES sys_users(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by BIGINT REFERENCES sys_users(id),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_kb_vector ON knowledge_articles USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_kb_type_system ON knowledge_articles(equipment_type, fault_system, is_featured);

-- 15. 培训管理相关表
CREATE TABLE IF NOT EXISTS training_courses (
    id BIGSERIAL PRIMARY KEY,
    course_code VARCHAR(64) NOT NULL UNIQUE,
    course_name VARCHAR(128) NOT NULL,
    course_category VARCHAR(64) NOT NULL,
    planned_hours NUMERIC(4, 1) NOT NULL,
    description TEXT,
    material_file_id BIGINT REFERENCES equipment_files(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT REFERENCES sys_users(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by BIGINT REFERENCES sys_users(id),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS training_course_cases (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT NOT NULL REFERENCES training_courses(id) ON DELETE CASCADE,
    article_id BIGINT NOT NULL REFERENCES knowledge_articles(id) ON DELETE CASCADE,
    UNIQUE (course_id, article_id)
);

CREATE TABLE IF NOT EXISTS training_records (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT NOT NULL REFERENCES training_courses(id),
    training_date DATE NOT NULL,
    instructor_name VARCHAR(64) NOT NULL,
    location VARCHAR(128) NOT NULL,
    live_photo_id BIGINT REFERENCES equipment_files(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT REFERENCES sys_users(id)
);

CREATE TABLE IF NOT EXISTS training_user_scores (
    id BIGSERIAL PRIMARY KEY,
    training_record_id BIGINT NOT NULL REFERENCES training_records(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES sys_users(id),
    assessment_type VARCHAR(32) NOT NULL,
    score NUMERIC(5, 2) NOT NULL,
    is_passed BOOLEAN NOT NULL,
    need_retraining BOOLEAN NOT NULL DEFAULT FALSE,
    retraining_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 16. 通知策略与防重发信表
CREATE TABLE IF NOT EXISTS maintenance_notify_configs (
    id BIGSERIAL PRIMARY KEY,
    lead_days INT NOT NULL UNIQUE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    target_role_group VARCHAR(32) NOT NULL DEFAULT 'ALL',
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by BIGINT REFERENCES sys_users(id)
);

CREATE TABLE IF NOT EXISTS maintenance_notify_logs (
    id BIGSERIAL PRIMARY KEY,
    equipment_id BIGINT NOT NULL REFERENCES equipments(id),
    task_id BIGINT REFERENCES maintenance_tasks(id),
    target_notify_date DATE NOT NULL,
    notify_stage INT NOT NULL,
    recipient_email VARCHAR(128) NOT NULL,
    sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
    UNIQUE (equipment_id, target_notify_date, notify_stage, recipient_email)
);

-- 17. 系统 SMTP 邮件服务器配置表 (SWR-SYS-001)
CREATE TABLE IF NOT EXISTS sys_smtp_configs (
    id BIGSERIAL PRIMARY KEY,
    smtp_host VARCHAR(128) NOT NULL,
    smtp_port INT NOT NULL DEFAULT 465,
    smtp_user VARCHAR(128) NOT NULL,
    smtp_pass VARCHAR(255) NOT NULL,
    sender_name VARCHAR(64) NOT NULL DEFAULT 'MaintainWise 智能运维中心',
    use_ssl BOOLEAN NOT NULL DEFAULT TRUE,
    use_tls BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by BIGINT REFERENCES sys_users(id)
);

-- ==============================================================================
-- 种子数据初始化 (Seed Data)
-- ==============================================================================

-- 1. 默认超级管理员 (admin / MaintainWiseAdmin@2026)
-- bcrypt hash cost 12: $2b$12$K8qN5dEw.3zQ5fHhF09uNuW8jCgP0Gg2pU6xZk3eE1lQo4qE5fHhe (示例)
INSERT INTO sys_users (username, password_hash, full_name, employee_no, email, phone, role_code, work_type, is_active, force_change_password)
VALUES 
('admin', '$2b$12$mogIHk0bHVz1ZXKSdSNLOOqYra.SPoxk5Sc0gMPREPI/mkOqJGEhK', '系统超级管理员', 'EMP-ADMIN-001', 'admin@factory.com', '13800000000', 'ADMIN', 'GENERAL', TRUE, TRUE)
ON CONFLICT (username) DO NOTHING;

-- 2. 默认层级拓扑分类树节点 (工厂 -> 部门 -> 系统)
INSERT INTO equipment_locations (id, parent_id, location_name, location_code, level_depth, node_type, tree_path, is_leaf, sort_order)
VALUES 
(1, NULL, '总装制造工厂', 'LOC-FAC-01', 1, 'FACTORY', '/1/', FALSE, 1),
(2, 1, '智能制造运维部', 'LOC-DEP-01', 2, 'DEPARTMENT', '/1/2/', FALSE, 1),
(3, 2, '主排风动力循环系统', 'LOC-SYS-01', 3, 'SYSTEM', '/1/2/3/', TRUE, 1),
(4, 3, '工位A1 (自动上下料工位)', 'LOC-STN-A1', 4, 'SYSTEM', '/1/2/3/4/', TRUE, 1)
ON CONFLICT (id) DO NOTHING;

-- 3. 默认到期通知提醒策略 (提前7天、3天、1天及当天)
INSERT INTO maintenance_notify_configs (lead_days, is_enabled, target_role_group)
VALUES 
(7, TRUE, 'ALL'),
(3, TRUE, 'ALL'),
(1, TRUE, 'ALL'),
(0, TRUE, 'ALL')
ON CONFLICT (lead_days) DO NOTHING;

-- 4. 默认 SMTP 邮件服务器配置 (SWR-SYS-001)
INSERT INTO sys_smtp_configs (id, smtp_host, smtp_port, smtp_user, smtp_pass, sender_name, use_ssl, use_tls, is_active)
VALUES 
(1, 'smtp.maintainwise.com', 465, 'noreply@maintainwise.com', 'InitialSmtpAuth2026', 'MaintainWise 智能运维中心', TRUE, FALSE, TRUE)
ON CONFLICT (id) DO NOTHING;

-- 序列号重置
SELECT setval('equipment_locations_id_seq', (SELECT MAX(id) FROM equipment_locations));
SELECT setval('sys_users_id_seq', (SELECT MAX(id) FROM sys_users));
SELECT setval('sys_smtp_configs_id_seq', (SELECT MAX(id) FROM sys_smtp_configs));
