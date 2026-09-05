<template>
  <div class="system-view">
    <div class="page-header">
      <div class="header-titles">
        <h2>系统管理与合规审计配置</h2>
        <p>SMTP 邮件自检发信、文件安全存储与 180 天只读操作审计日志 (SWR-SYS-001/005/006)</p>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 左侧: SMTP 发信自检 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="smtp-card">
          <template #header>
            <div class="card-header">
              <el-icon color="#409eff"><Message /></el-icon>
              <span class="header-title">SMTP 告警邮件自检 (SWR-SYS-001)</span>
            </div>
          </template>

          <el-form label-position="top">
            <el-form-item label="测试目标收件邮箱" required>
              <el-input v-model="testEmail" placeholder="如: admin@factory.com" clearable />
            </el-form-item>

            <div class="smtp-info">
              <p>预警触发策略：</p>
              <ul>
                <li>维护工单到期前 3 天定时派送通知</li>
                <li>故障单 SLA 超期立即向主管升级发信</li>
                <li>内置 24 小时防重幂等校验机制</li>
              </ul>
            </div>

            <el-button
              type="primary"
              :loading="sendingMail"
              style="width: 100%; margin-top: 12px;"
              @click="handleSendTestEmail"
            >
              发送自检测试邮件
            </el-button>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧: 180天审计日志 (SWR-SYS-005) -->
      <el-col :xs="24" :md="16">
        <el-card shadow="never" class="audit-card">
          <template #header>
            <div class="card-header">
              <el-icon color="#67c23a"><DocumentChecked /></el-icon>
              <span class="header-title">180天只读操作审计日志 (SWR-SYS-005)</span>
              <el-button size="small" link :icon="Refresh" @click="fetchAuditLogs" style="margin-left: auto;" />
            </div>
          </template>

          <el-table :data="auditLogs" v-loading="loadingLogs" border stripe size="small">
            <el-table-column prop="created_at" label="操作时间" width="160" />
            <el-table-column prop="username" label="操作账号" width="120" />
            <el-table-column prop="client_ip" label="客户端IP" width="120" />
            <el-table-column prop="module_name" label="业务模块" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ row.module_name || 'SYSTEM' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="action_type" label="动作类型" width="110" />
            <el-table-column prop="request_url" label="请求接口URL" min-width="180" />
            <el-table-column prop="status_code" label="响应码" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status_code === 200 ? 'success' : 'danger'">
                  {{ row.status_code }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import apiClient from '@/api/client';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Message, DocumentChecked, Refresh } from '@element-plus/icons-vue';

const testEmail = ref('factory_admin@maintainwise.com');
const sendingMail = ref(false);

const loadingLogs = ref(false);
const auditLogs = ref<any[]>([]);

const handleSendTestEmail = async () => {
  if (!testEmail.value) {
    ElMessage.warning('请输入收件邮箱');
    return;
  }
  sendingMail.value = true;
  try {
    const res = await apiClient.post<any, any>('/system/smtp/test', {
      to_email: testEmail.value,
    });
    if (res.code === 200) {
      ElMessageBox.alert(res.message, 'SMTP 发信自检成功', { type: 'success' });
    }
  } catch (err) {
    console.error(err);
  } finally {
    sendingMail.value = false;
  }
};

const fetchAuditLogs = async () => {
  loadingLogs.value = true;
  try {
    const res = await apiClient.get<any, any>('/system/audit-logs?limit=25');
    if (res.code === 200 && res.data?.items) {
      auditLogs.value = res.data.items;
    }
  } catch (err) {
    console.error(err);
  } finally {
    loadingLogs.value = false;
  }
};

onMounted(() => {
  fetchAuditLogs();
});
</script>

<style scoped>
.system-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  background: #fff;
  padding: 16px 20px;
  border-radius: 8px;
}

.header-titles h2 {
  margin: 0 0 4px 0;
  font-size: 20px;
  color: #1e293b;
}

.header-titles p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.smtp-card, .audit-card {
  min-height: calc(100vh - 200px);
}

.smtp-info {
  background-color: #f8fafc;
  padding: 12px;
  border-radius: 6px;
  font-size: 13px;
  color: #64748b;
}

.smtp-info p {
  margin: 0 0 6px 0;
  font-weight: 600;
}

.smtp-info ul {
  margin: 0;
  padding-left: 18px;
  line-height: 1.6;
}
</style>
