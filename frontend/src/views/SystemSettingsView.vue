<template>
  <div class="system-view">
    <div class="page-header">
      <div class="header-titles">
        <h2>系统设置</h2>
        <p>SMTP 邮件服务器配置与自检、系统运行环境、数据安全与 180 天只读审计日志 (SWR-SYS-001/005/006)</p>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 左侧: SMTP 邮件服务器可视化配置与自检 (SWR-SYS-001) -->
      <el-col :xs="24" :lg="11">
        <el-card shadow="never" class="config-card">
          <template #header>
            <div class="card-header">
              <el-icon color="#409eff"><Setting /></el-icon>
              <span class="header-title">SMTP 邮件服务器配置 (SWR-SYS-001)</span>
              <el-tag :type="smtpForm.is_active ? 'success' : 'info'" size="small" style="margin-left: auto;">
                {{ smtpForm.is_active ? '服务已启用' : '服务已停用' }}
              </el-tag>
            </div>
          </template>

          <el-form :model="smtpForm" label-position="top" size="default" v-loading="loadingConfig">
            <el-row :gutter="12">
              <el-col :span="16">
                <el-form-item label="SMTP 服务器主机 (Host)" required>
                  <el-input
                    v-model="smtpForm.smtp_host"
                    placeholder="如: smtp.exmail.qq.com, smtp.163.com"
                    clearable
                  />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="端口号 (Port)" required>
                  <el-input-number
                    v-model="smtpForm.smtp_port"
                    :min="1"
                    :max="65535"
                    style="width: 100%;"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="发信认证账号 / 邮箱" required>
                  <el-input
                    v-model="smtpForm.smtp_user"
                    placeholder="如: notice@maintainwise.com"
                    clearable
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="授权码 / 密码">
                  <el-input
                    v-model="smtpForm.smtp_pass"
                    type="password"
                    show-password
                    placeholder="留空或保持 ****** 则不变更原密码"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="12">
              <el-col :span="14">
                <el-form-item label="发件人显示昵称">
                  <el-input
                    v-model="smtpForm.sender_name"
                    placeholder="如: MaintainWise 智能运维中心"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="10">
                <el-form-item label="启用邮件告警服务">
                  <el-switch
                    v-model="smtpForm.is_active"
                    active-text="启用"
                    inactive-text="停用"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="安全传输协议">
              <div class="security-options">
                <el-checkbox v-model="smtpForm.use_ssl">启用 SSL/TLS 加密 (推荐端口 465)</el-checkbox>
                <el-checkbox v-model="smtpForm.use_tls">启用 STARTTLS 加密 (推荐端口 587)</el-checkbox>
              </div>
            </el-form-item>

            <div class="form-actions">
              <el-button type="primary" :icon="Check" :loading="savingConfig" @click="handleSaveConfig">
                保存邮件服务器配置
              </el-button>
              <el-button :icon="Refresh" @click="fetchSmtpConfig">
                重置
              </el-button>
            </div>
          </el-form>

          <el-divider content-position="left">
            <span style="font-size: 13px; color: #64748b;">在线连通性测试与发信自检</span>
          </el-divider>

          <div class="test-email-box">
            <el-input
              v-model="testEmail"
              placeholder="输入接收自检邮件的目标邮箱，如: admin@factory.com"
              clearable
            >
              <template #append>
                <el-button
                  type="success"
                  :icon="Promotion"
                  :loading="sendingMail"
                  @click="handleSendTestEmail"
                >
                  发送自检测试
                </el-button>
              </template>
            </el-input>
            <div class="smtp-hints">
              <p>📌 动态配置说明：</p>
              <ul>
                <li>在页面修改并保存后，调度中心将<strong>无需重启服务，即刻热生效</strong>。</li>
                <li>维保到期提前通知 (7/3/1/0 天) 与 SLA 升级告警将统一使用此配置发信。</li>
                <li>每次保存动作均会自动记录于右侧防篡改审计日志流水中。</li>
              </ul>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧: 180天只读操作审计日志 (SWR-SYS-005) -->
      <el-col :xs="24" :lg="13">
        <el-card shadow="never" class="audit-card">
          <template #header>
            <div class="card-header">
              <el-icon color="#67c23a"><DocumentChecked /></el-icon>
              <span class="header-title">180天只读操作审计日志 (SWR-SYS-005)</span>
              <el-button size="small" link :icon="Refresh" @click="fetchAuditLogs" style="margin-left: auto;">
                刷新日志
              </el-button>
            </div>
          </template>

          <el-table :data="auditLogs" v-loading="loadingLogs" border stripe size="small" height="calc(100vh - 280px)">
            <el-table-column prop="created_at" label="操作时间" width="160" />
            <el-table-column prop="username" label="操作账号" width="110" />
            <el-table-column prop="client_ip" label="客户端IP" width="110" />
            <el-table-column prop="module_name" label="业务模块" width="130">
              <template #default="{ row }">
                <el-tag size="small" :type="row.module_name?.includes('SMTP') ? 'warning' : 'info'">
                  {{ row.module_name || 'SYSTEM' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="action_type" label="动作类型" width="90" />
            <el-table-column prop="request_url" label="请求接口" min-width="160" show-overflow-tooltip />
            <el-table-column prop="status_code" label="响应码" width="75">
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
import { ref, reactive, onMounted } from 'vue';
import apiClient from '@/api/client';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Setting, DocumentChecked, Refresh, Check, Promotion } from '@element-plus/icons-vue';

interface SmtpConfigState {
  id?: number;
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_pass: string;
  sender_name: string;
  use_ssl: boolean;
  use_tls: boolean;
  is_active: boolean;
}

const smtpForm = reactive<SmtpConfigState>({
  smtp_host: '',
  smtp_port: 465,
  smtp_user: '',
  smtp_pass: '******',
  sender_name: 'MaintainWise 智能运维中心',
  use_ssl: true,
  use_tls: false,
  is_active: true,
});

const loadingConfig = ref(false);
const savingConfig = ref(false);
const testEmail = ref('admin@factory.com');
const sendingMail = ref(false);

const loadingLogs = ref(false);
const auditLogs = ref<any[]>([]);

// 1. 获取已保存的 SMTP 服务器配置 (密码脱敏)
const fetchSmtpConfig = async () => {
  loadingConfig.value = true;
  try {
    const res = await apiClient.get<any, any>('/system/smtp/config');
    if (res.code === 200 && res.data) {
      smtpForm.id = res.data.id;
      smtpForm.smtp_host = res.data.smtp_host;
      smtpForm.smtp_port = res.data.smtp_port;
      smtpForm.smtp_user = res.data.smtp_user;
      smtpForm.smtp_pass = res.data.smtp_pass_masked || '******';
      smtpForm.sender_name = res.data.sender_name;
      smtpForm.use_ssl = res.data.use_ssl;
      smtpForm.use_tls = res.data.use_tls;
      smtpForm.is_active = res.data.is_active;
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '获取 SMTP 配置失败');
  } finally {
    loadingConfig.value = false;
  }
};

// 2. 页面保存 SMTP 服务器配置
const handleSaveConfig = async () => {
  if (!smtpForm.smtp_host || !smtpForm.smtp_user) {
    ElMessage.warning('请填写 SMTP 服务器主机与发信账号！');
    return;
  }
  savingConfig.value = true;
  try {
    const res = await apiClient.post<any, any>('/system/smtp/config', {
      smtp_host: smtpForm.smtp_host,
      smtp_port: smtpForm.smtp_port,
      smtp_user: smtpForm.smtp_user,
      smtp_pass: smtpForm.smtp_pass,
      sender_name: smtpForm.sender_name,
      use_ssl: smtpForm.use_ssl,
      use_tls: smtpForm.use_tls,
      is_active: smtpForm.is_active,
    });
    if (res.code === 200) {
      ElMessage.success(res.message || 'SMTP 配置保存成功！');
      smtpForm.smtp_pass = '******';
      fetchAuditLogs(); // 刷新审计日志
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '保存配置失败');
  } finally {
    savingConfig.value = false;
  }
};

// 3. 在线连通性自检
const handleSendTestEmail = async () => {
  if (!testEmail.value) {
    ElMessage.warning('请输入目标测试收件邮箱');
    return;
  }
  sendingMail.value = true;
  try {
    const res = await apiClient.post<any, any>('/system/smtp/test', {
      to_email: testEmail.value,
      smtp_host: smtpForm.smtp_host,
      smtp_port: smtpForm.smtp_port,
      smtp_user: smtpForm.smtp_user,
      smtp_pass: smtpForm.smtp_pass,
      sender_name: smtpForm.sender_name,
      use_ssl: smtpForm.use_ssl,
      use_tls: smtpForm.use_tls,
    });
    if (res.code === 200) {
      ElMessageBox.alert(res.message, 'SMTP 发信自检成功', { type: 'success' });
    }
  } catch (err: any) {
    ElMessageBox.alert(err.response?.data?.message || '测试发信失败，请检查配置与网络', '发信失败', { type: 'error' });
  } finally {
    sendingMail.value = false;
  }
};

// 4. 审计日志查询
const fetchAuditLogs = async () => {
  loadingLogs.value = true;
  try {
    const res = await apiClient.get<any, any>('/system/audit-logs?limit=30');
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
  fetchSmtpConfig();
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

.config-card, .audit-card {
  min-height: calc(100vh - 200px);
}

.security-options {
  display: flex;
  gap: 20px;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 10px;
  margin-bottom: 12px;
}

.test-email-box {
  margin-top: 8px;
}

.smtp-hints {
  background-color: #f8fafc;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  color: #64748b;
  margin-top: 12px;
}

.smtp-hints p {
  margin: 0 0 6px 0;
  font-weight: 600;
}

.smtp-hints ul {
  margin: 0;
  padding-left: 18px;
  line-height: 1.6;
}
</style>

