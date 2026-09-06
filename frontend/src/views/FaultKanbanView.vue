<template>
  <div class="fault-kanban-view">
    <!-- 头部工具栏 -->
    <div class="page-header">
      <div class="header-titles">
        <h2>故障协同与流转看板</h2>
        <p>支持多角色状态流转、并发抢单乐观锁、300ms 实时智能推荐与知识库沉淀 (SWR-FLT-003/004/005/006)</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" @click="fetchFaults">刷 新</el-button>
        <el-button type="danger" :icon="Plus" @click="openReportDialog">新建故障报修</el-button>
      </div>
    </div>

    <!-- 故障多维检索过滤栏 -->
    <div class="search-toolbar" style="display: flex; gap: 12px; align-items: center; background: #fff; padding: 12px 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索故障编码 / 标题 / 部件 / 描述"
        prefix-icon="Search"
        clearable
        style="width: 280px;"
      />
      <el-select v-model="searchSeverity" placeholder="全部严重等级" clearable style="width: 150px;">
        <el-option label="全部等级" value="" />
        <el-option label="紧急停线 (CRITICAL)" value="CRITICAL" />
        <el-option label="严重故障 (MAJOR)" value="MAJOR" />
        <el-option label="轻微故障 (MINOR)" value="MINOR" />
      </el-select>
      <el-input
        v-model="searchSystem"
        placeholder="所属系统 (如: 驱动系统)"
        clearable
        style="width: 200px;"
      />
      <el-button type="primary" :icon="Search">查 询</el-button>
      <el-button @click="searchKeyword = ''; searchSeverity = ''; searchSystem = ''">重 置</el-button>
      <div style="flex: 1;"></div>
      <span style="font-size: 13px; color: #64748b;">
        当前匹配共 <strong>{{ allFilteredCount }}</strong> 起故障工单
      </span>
    </div>

    <!-- 泳道看板 -->
    <div class="kanban-board" v-loading="loading">
      <!-- 泳道 1: 待认领池 (OPEN) -->
      <div class="kanban-lane lane-open">
        <div class="lane-header">
          <div class="lane-title">
            <span class="lane-indicator open"></span>
            <span>待抢单池 (OPEN)</span>
          </div>
          <el-tag size="small" type="danger" effect="plain">{{ getLaneItems('OPEN').length }}</el-tag>
        </div>

        <div class="lane-content">
          <div
            v-for="item in getLaneItems('OPEN')"
            :key="item.id"
            class="kanban-card"
          >
            <div class="card-top">
              <span class="fault-code">{{ item.fault_code }}</span>
              <el-tag size="small" :type="getSeverityTag(item.severity_level)">{{ item.severity_level }}</el-tag>
            </div>
            <h4 class="card-title">{{ item.fault_title }}</h4>
            <p class="card-desc">{{ item.fault_desc }}</p>
            <div class="card-meta">
              <span>系统: {{ item.fault_system }} / {{ item.fault_part }}</span>
              <span v-if="item.is_sla_response_breached" class="sla-alert">SLA 响应破线!</span>
            </div>
            <div class="card-footer">
              <el-button
                v-permission="['ADMIN', 'ENGINEER']"
                type="primary"
                size="small"
                class="touch-target-sm"
                @click="handleClaim(item)"
              >
                ⚡ 并发抢单认领
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 泳道 2: 抢修中 (IN_PROGRESS) -->
      <div class="kanban-lane lane-progress">
        <div class="lane-header">
          <div class="lane-title">
            <span class="lane-indicator progress"></span>
            <span>处置抢修中 (IN_PROGRESS)</span>
          </div>
          <el-tag size="small" type="warning" effect="plain">{{ getLaneItems('IN_PROGRESS').length }}</el-tag>
        </div>

        <div class="lane-content">
          <div
            v-for="item in getLaneItems('IN_PROGRESS')"
            :key="item.id"
            class="kanban-card card-progress"
          >
            <div class="card-top">
              <span class="fault-code">{{ item.fault_code }}</span>
              <el-tag size="small" :type="getSeverityTag(item.severity_level)">{{ item.severity_level }}</el-tag>
            </div>
            <h4 class="card-title">{{ item.fault_title }}</h4>
            <p class="card-desc">{{ item.fault_desc }}</p>
            <div class="card-meta">
              <span>责任工程师: ID-{{ item.assigned_engineer_id || '已认领' }}</span>
              <span v-if="item.is_sla_resolve_breached" class="sla-alert">SLA 解决超时!</span>
            </div>
            <div class="card-footer">
              <el-button
                v-permission="['ADMIN', 'ENGINEER']"
                type="success"
                size="small"
                @click="openResolveDialog(item)"
              >
                🛠️ 维修复盘提交
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 泳道 3: 已解决待复核 (RESOLVED) -->
      <div class="kanban-lane lane-resolved">
        <div class="lane-header">
          <div class="lane-title">
            <span class="lane-indicator resolved"></span>
            <span>已排查待复核 (RESOLVED)</span>
          </div>
          <el-tag size="small" type="success" effect="plain">{{ getLaneItems('RESOLVED').length }}</el-tag>
        </div>

        <div class="lane-content">
          <div
            v-for="item in getLaneItems('RESOLVED')"
            :key="item.id"
            class="kanban-card"
          >
            <div class="card-top">
              <span class="fault-code">{{ item.fault_code }}</span>
              <el-tag v-if="item.is_featured_case" size="small" type="warning">典型案例★</el-tag>
            </div>
            <h4 class="card-title">{{ item.fault_title }}</h4>
            <p class="solution-text"><strong>排查步骤:</strong> {{ item.solution_steps }}</p>
            <div class="card-meta">
              <span>停机时长: {{ item.downtime_minutes }} min</span>
            </div>
            <div class="card-footer">
              <el-button
                v-permission="['ADMIN', 'ENGINEER']"
                type="primary"
                plain
                size="small"
                @click="handleCloseFault(item)"
              >
                ✔️ 验收归档关闭
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 泳道 4: 已关闭归档 (CLOSED) -->
      <div class="kanban-lane lane-closed">
        <div class="lane-header">
          <div class="lane-title">
            <span class="lane-indicator closed"></span>
            <span>知识库沉淀与闭环 (CLOSED)</span>
          </div>
          <el-tag size="small" type="info" effect="plain">{{ getLaneItems('CLOSED').length }}</el-tag>
        </div>

        <div class="lane-content">
          <div
            v-for="item in getLaneItems('CLOSED')"
            :key="item.id"
            class="kanban-card card-closed"
          >
            <div class="card-top">
              <span class="fault-code">{{ item.fault_code }}</span>
              <el-tag size="small" type="info">已沉淀</el-tag>
            </div>
            <h4 class="card-title">{{ item.fault_title }}</h4>
            <p class="card-desc">根因: {{ item.root_cause }}</p>
            <div class="card-meta">
              <span>闭环于: {{ formatTime(item.closed_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 故障上报与 300ms 智能推荐抽屉 (SWR-FLT-002/003) -->
    <el-dialog
      v-model="reportDialogVisible"
      title="提报设备突发故障 (300ms 实时智能案例推荐)"
      width="880px"
      append-to-body
    >
      <el-row :gutter="24">
        <!-- 左侧提报表单 -->
        <el-col :span="14">
          <el-form ref="reportFormRef" :model="reportForm" :rules="reportRules" label-position="top">
            <el-form-item label="故障设备ID" prop="equipment_id">
              <el-input-number v-model="reportForm.equipment_id" :min="1" style="width: 100%;" />
            </el-form-item>

            <el-form-item label="严重级别" prop="severity_level">
              <el-select v-model="reportForm.severity_level" style="width: 100%;">
                <el-option label="轻微故障 (MINOR)" value="MINOR" />
                <el-option label="严重故障 (MAJOR)" value="MAJOR" />
                <el-option label="紧急致命停线 (CRITICAL)" value="CRITICAL" />
              </el-select>
            </el-form-item>

            <el-form-item label="所属系统与部件" required>
              <el-row :gutter="12">
                <el-col :span="12">
                  <el-input v-model="reportForm.fault_system" placeholder="系统 (如: 传动系统)" />
                </el-col>
                <el-col :span="12">
                  <el-input v-model="reportForm.fault_part" placeholder="部件 (如: 主轴承)" />
                </el-col>
              </el-row>
            </el-form-item>

            <el-form-item label="故障简述标题" prop="fault_title">
              <el-input v-model="reportForm.fault_title" placeholder="简要概括故障现象" />
            </el-form-item>

            <el-form-item label="详细现象描述 (实时防抖推荐触发)" prop="fault_desc">
              <el-input
                v-model="reportForm.fault_desc"
                type="textarea"
                :rows="4"
                placeholder="录入详细现象，系统将在 300ms 内自动匹配知识库相似历史方案..."
                @input="handleDescInput"
              />
            </el-form-item>

            <el-form-item label="故障现场照片证据 (选填)">
              <el-upload
                :http-request="handleReportPhotoUpload"
                :show-file-list="false"
                accept="image/*"
              >
                <el-button type="primary" plain :icon="Upload">
                  {{ reportPhotoName ? `已上传: ${reportPhotoName}` : '点击上传故障现场照片' }}
                </el-button>
              </el-upload>
            </el-form-item>
          </el-form>
        </el-col>

        <!-- 右侧智能排查推荐卡片 -->
        <el-col :span="10">
          <div class="recommend-panel">
            <div class="panel-header">
              <el-icon color="#409eff"><Reading /></el-icon>
              <span>实时知识库推荐匹配 (SWR-FLT-003)</span>
            </div>

            <div v-if="recommendLoading" class="rec-loading">
              <el-icon class="is-loading"><Loading /></el-icon> 正在检索向量与案例库...
            </div>

            <div v-else-if="similarCases.length === 0" class="rec-empty">
              <p>在左侧输入现象描述，系统将自动推荐排查建议</p>
            </div>

            <div v-else class="rec-cases-list">
              <div
                v-for="c in similarCases"
                :key="c.case_id"
                class="rec-case-item"
              >
                <div class="case-header">
                  <span class="case-title">{{ c.fault_title }}</span>
                  <el-tag size="small" type="success">{{ Math.round(c.similarity_score * 100) }}% 相似</el-tag>
                </div>
                <div class="case-root"><strong>历史根因:</strong> {{ c.root_cause }}</div>
                <div class="case-solution"><strong>推荐排查:</strong> {{ c.solution_steps }}</div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <template #footer>
        <el-button @click="reportDialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="reporting" @click="submitReport">提 报 工 单</el-button>
      </template>
    </el-dialog>

    <!-- 维修复盘弹窗 (SWR-FLT-006 / 007) -->
    <el-dialog
      v-model="resolveDialogVisible"
      title="维修复盘与知识沉淀"
      width="600px"
      append-to-body
    >
      <el-form ref="resolveFormRef" :model="resolveForm" :rules="resolveRules" label-position="top">
        <el-form-item label="故障根本原因 (必填 - SWR-FLT-006)" prop="root_cause">
          <el-input
            v-model="resolveForm.root_cause"
            type="textarea"
            :rows="3"
            placeholder="详细分析导致本次故障的根本原因（如零件磨损、润滑失效、参数漂移）"
          />
        </el-form-item>

        <el-form-item label="维修解决步骤 (必填)" prop="solution_steps">
          <el-input
            v-model="resolveForm.solution_steps"
            type="textarea"
            :rows="3"
            placeholder="列出标准维修操作步骤，将自动同步至排查知识库"
          />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="停机时长 (分钟)">
              <el-input-number v-model="resolveForm.downtime_minutes" :min="0" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="标定为典型案例 (SWR-FLT-007)">
              <el-switch v-model="resolveForm.is_featured_case" active-text="入选培训典型案例库" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="解决故障方法/凭据照片 (选填)">
          <el-upload
            :http-request="handleResolvePhotoUpload"
            :show-file-list="false"
            accept="image/*"
          >
            <el-button type="success" plain :icon="Upload">
              {{ resolvePhotoName ? `已上传: ${resolvePhotoName}` : '点击上传解决后凭证照片' }}
            </el-button>
          </el-upload>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="resolveDialogVisible = false">取 消</el-button>
        <el-button type="success" :loading="resolving" @click="submitResolve">提交复盘并沉淀知识</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import apiClient from '@/api/client';
import { ElMessage, ElMessageBox, FormInstance } from 'element-plus';
import {
  Refresh,
  Plus,
  Reading,
  Loading,
  Search,
  Upload,
} from '@element-plus/icons-vue';

const route = useRoute();
const loading = ref(false);
const allFaults = ref<any[]>([]);

const reportDialogVisible = ref(false);
const reporting = ref(false);
const reportFormRef = ref<FormInstance>();
const reportPhotoName = ref('');
const reportForm = reactive({
  equipment_id: 1,
  severity_level: 'MAJOR',
  fault_system: '驱动系统',
  fault_part: '离合器轴承',
  fault_title: '',
  fault_desc: '',
  evidence_file_id: null as number | null,
});

const searchKeyword = ref('');
const searchSeverity = ref('');
const searchSystem = ref('');

const allFilteredCount = computed(() => {
  return ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'].reduce((sum, st) => sum + getLaneItems(st).length, 0);
});

const handleReportPhotoUpload = async (options: any) => {
  const { file } = options;
  const formData = new FormData();
  formData.append('file', file);
  formData.append('file_tag', 'FAULT_IMG');
  try {
    const res = await apiClient.post<any, any>('/system/files/upload', formData);
    if (res.code === 200 && res.data?.file_id) {
      reportForm.evidence_file_id = res.data.file_id;
      reportPhotoName.value = file.name;
      ElMessage.success('现场照片上传成功');
    }
  } catch (err) {
    ElMessage.error('照片上传失败');
  }
};

const handleResolvePhotoUpload = async (options: any) => {
  const { file } = options;
  const formData = new FormData();
  formData.append('file', file);
  formData.append('file_tag', 'FAULT_IMG');
  try {
    const res = await apiClient.post<any, any>('/system/files/upload', formData);
    if (res.code === 200 && res.data?.file_id) {
      resolveForm.solution_photo_file_id = res.data.file_id;
      resolvePhotoName.value = file.name;
      ElMessage.success('解决凭据照片上传成功');
    }
  } catch (err) {
    ElMessage.error('照片上传失败');
  }
};

const reportRules = {
  equipment_id: [{ required: true, message: '请指定设备', trigger: 'blur' }],
  fault_title: [{ required: true, message: '请输入故障标题', trigger: 'blur' }],
  fault_desc: [{ required: true, message: '请输入详细描述', trigger: 'blur' }],
};

// 300ms 防抖推荐逻辑 (SWR-FLT-003)
let debounceTimer: any = null;
const recommendLoading = ref(false);
const similarCases = ref<any[]>([]);

const handleDescInput = () => {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    if (!reportForm.fault_desc || reportForm.fault_desc.trim().length < 2) {
      similarCases.value = [];
      return;
    }
    recommendLoading.value = true;
    try {
      const res = await apiClient.post<any, any>(
        `/faults/recommend-similar?equipment_type=FAN&model_spec=Y4-73&fault_desc=${encodeURIComponent(reportForm.fault_desc)}&fault_part=${encodeURIComponent(reportForm.fault_part)}`
      );
      if (res.code === 200 && res.data) {
        similarCases.value = res.data;
      }
    } catch (err) {
      console.error(err);
    } finally {
      recommendLoading.value = false;
    }
  }, 300);
};

// 维修复盘
const resolveDialogVisible = ref(false);
const resolving = ref(false);
const resolvePhotoName = ref('');
const currentResolveFaultId = ref<number | null>(null);
const resolveFormRef = ref<FormInstance>();
const resolveForm = reactive({
  root_cause: '',
  solution_steps: '',
  downtime_minutes: 30,
  is_featured_case: false,
  solution_photo_file_id: null as number | null,
});

const resolveRules = {
  root_cause: [{ required: true, message: '根本原因必填', trigger: 'blur' }],
  solution_steps: [{ required: true, message: '解决步骤必填', trigger: 'blur' }],
};

const getLaneItems = (status: string) => {
  return allFaults.value.filter((f) => {
    if (f.status !== status) return false;
    if (searchSeverity.value && f.severity_level !== searchSeverity.value) return false;
    if (searchSystem.value && !f.fault_system?.toLowerCase().includes(searchSystem.value.toLowerCase())) return false;
    if (searchKeyword.value) {
      const kw = searchKeyword.value.toLowerCase();
      const matchCode = f.fault_code?.toLowerCase().includes(kw);
      const matchTitle = f.fault_title?.toLowerCase().includes(kw);
      const matchDesc = f.fault_desc?.toLowerCase().includes(kw);
      const matchPart = f.fault_part?.toLowerCase().includes(kw);
      if (!matchCode && !matchTitle && !matchDesc && !matchPart) return false;
    }
    return true;
  });
};

const getSeverityTag = (sev: string) => {
  switch (sev) {
    case 'CRITICAL': return 'danger';
    case 'MAJOR': return 'warning';
    default: return 'info';
  }
};

const formatTime = (t?: string) => {
  if (!t) return '-';
  return t.replace('T', ' ').substring(0, 16);
};

const fetchFaults = async () => {
  loading.value = true;
  try {
    const res = await apiClient.get<any, any>('/faults?limit=100');
    if (res.code === 200 && res.data?.items) {
      allFaults.value = res.data.items;
    }
  } catch (err) {
    console.error(err);
  } finally {
    loading.value = false;
  }
};

// 并发抢单乐观锁 (SWR-FLT-005)
const handleClaim = async (fault: any) => {
  try {
    const res = await apiClient.put<any, any>(`/faults/${fault.id}/claim`);
    if (res.code === 200) {
      ElMessage.success('工单抢单认领成功！工单状态已进入抢修中');
      fetchFaults();
    }
  } catch (err: any) {
    // 30002 乐观锁冲突
    if (err?.code === 30002) {
      ElMessageBox.alert(
        `很遗憾，该工单刚刚已被其他工程师成功抢单！\n当前状态: ${err.message}`,
        '抢单冲突 (乐观锁保护)',
        { type: 'warning' }
      );
      fetchFaults();
    }
  }
};

const openReportDialog = () => {
  reportPhotoName.value = '';
  reportForm.evidence_file_id = null;
  reportDialogVisible.value = true;
};

const submitReport = async () => {
  if (!reportFormRef.value) return;
  await reportFormRef.value.validate(async (valid) => {
    if (!valid) return;
    reporting.value = true;
    try {
      const res = await apiClient.post<any, any>('/faults', reportForm);
      if (res.code === 200) {
        ElMessage.success('故障上报成功，已进入待处理池！');
        reportDialogVisible.value = false;
        fetchFaults();
      }
    } catch (err) {
      console.error(err);
    } finally {
      reporting.value = false;
    }
  });
};

const openResolveDialog = (fault: any) => {
  currentResolveFaultId.value = fault.id;
  resolveForm.root_cause = fault.root_cause || '';
  resolveForm.solution_steps = fault.solution_steps || '';
  resolveForm.downtime_minutes = fault.downtime_minutes || 25;
  resolveForm.is_featured_case = fault.is_featured_case || false;
  resolveForm.solution_photo_file_id = null;
  resolvePhotoName.value = '';
  resolveDialogVisible.value = true;
};

const submitResolve = async () => {
  if (!resolveFormRef.value || !currentResolveFaultId.value) return;
  await resolveFormRef.value.validate(async (valid) => {
    if (!valid) return;
    resolving.value = true;
    try {
      const res = await apiClient.post<any, any>(`/faults/${currentResolveFaultId.value}/resolve`, resolveForm);
      if (res.code === 200) {
        ElMessage.success('维修复盘提交成功，并已自动沉淀入知识库！');
        resolveDialogVisible.value = false;
        fetchFaults();
      }
    } catch (err) {
      console.error(err);
    } finally {
      resolving.value = false;
    }
  });
};

const handleCloseFault = async (fault: any) => {
  try {
    await ElMessageBox.confirm('确认复核通过并正式归档该工单？', '提示', { type: 'info' });
    const res = await apiClient.put<any, any>(`/faults/${fault.id}/close`);
    if (res.code === 200) {
      ElMessage.success('工单已正式归档闭环');
      fetchFaults();
    }
  } catch (err) {
    // Cancelled
  }
};

onMounted(() => {
  fetchFaults();
  if (route.query.action === 'create') {
    openReportDialog();
  }
});
</script>

<style scoped>
.fault-kanban-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.header-actions {
  display: flex;
  gap: 12px;
}

.kanban-board {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  min-height: 600px;
}

@media (max-width: 1200px) {
  .kanban-board {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .kanban-board {
    grid-template-columns: 1fr;
  }
}

.kanban-lane {
  background-color: #f1f5f9;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  padding: 12px;
}

.lane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 2px solid #e2e8f0;
  margin-bottom: 12px;
}

.lane-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: #334155;
}

.lane-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.lane-indicator.open { background-color: #ef4444; }
.lane-indicator.progress { background-color: #f59e0b; }
.lane-indicator.resolved { background-color: #10b981; }
.lane-indicator.closed { background-color: #94a3b8; }

.lane-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  max-height: calc(100vh - 240px);
}

.kanban-card {
  background: #ffffff;
  border-radius: 8px;
  padding: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.fault-code {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.card-title {
  margin: 0;
  font-size: 15px;
  color: #1e293b;
  font-weight: 600;
}

.card-desc {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.4;
}

.solution-text {
  margin: 0;
  font-size: 12px;
  color: #15803d;
  background-color: #f0fdf4;
  padding: 6px 8px;
  border-radius: 4px;
}

.card-meta {
  font-size: 12px;
  color: #94a3b8;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sla-alert {
  color: #ef4444;
  font-weight: 700;
}

.card-footer {
  margin-top: 6px;
  display: flex;
  justify-content: flex-end;
}

.touch-target-sm {
  min-height: 36px;
}

.recommend-panel {
  background-color: #f8fafc;
  border-radius: 8px;
  padding: 14px;
  height: 100%;
  border: 1px solid #e2e8f0;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
  font-size: 14px;
}

.rec-loading, .rec-empty {
  font-size: 13px;
  color: #94a3b8;
  padding: 20px 0;
  text-align: center;
}

.rec-cases-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 320px;
  overflow-y: auto;
}

.rec-case-item {
  background: #ffffff;
  padding: 10px;
  border-radius: 6px;
  border-left: 3px solid #10b981;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.case-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.case-root, .case-solution {
  font-size: 12px;
  color: #475569;
  line-height: 1.4;
  margin-top: 2px;
}
</style>