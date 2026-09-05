<template>
  <div class="inspection-touch-view">
    <!-- 顶部状态栏与工作模式切换 -->
    <div class="touch-view-header">
      <div class="header-info">
        <div class="header-title-row">
          <h2>{{ activeMode === 'inspection' ? '车间现场维护单' : '设备运行工时填报' }}</h2>
          <el-radio-group v-model="activeMode" size="large" class="mode-switch-group">
            <el-radio-button value="inspection">
              <el-icon><DocumentChecked /></el-icon> 现场维护单
            </el-radio-button>
            <el-radio-button value="meter">
              <el-icon><Timer /></el-icon> 运行工时填报
            </el-radio-button>
          </el-radio-group>
        </div>
        <span class="sub-tip">
          {{
            activeMode === 'inspection'
              ? '工控平板与防误触优化模式 · 设备维护内容逐项核验 (SWR-MNT-007 / SWR-MNT-008)'
              : '非24h连续机台每日工时填报 · 预警阈值达标自动邮件触发与工单派发 (SWR-MNT-012)'
          }}
        </span>
      </div>

      <div v-if="activeMode === 'inspection'" class="header-actions">
        <el-button type="info" plain size="large" @click="resetForm">重 置</el-button>
        <el-button
          type="primary"
          size="large"
          :loading="submitting"
          class="submit-main-btn"
          @click="submitInspection"
        >
          提交维护单记录
        </el-button>
      </div>
      <div v-else class="header-actions">
        <el-button size="large" :icon="Refresh" @click="fetchOperatingOverview">刷新机台工时</el-button>
      </div>
    </div>

    <!-- ==================== 模式一：现场维护单打卡 ==================== -->
    <div v-if="activeMode === 'inspection'" class="inspection-mode-container">
      <!-- 任务选择与设备信息卡片 -->
      <el-card shadow="never" class="task-selector-card">
        <el-row :gutter="16" align="middle">
          <el-col :xs="24" :md="10">
            <div class="field-label">当前待执行任务：</div>
            <el-select
              v-model="selectedTaskId"
              placeholder="请选择或扫码待维护工单"
              size="large"
              style="width: 100%;"
              @change="handleTaskChange"
            >
              <el-option
                v-for="task in myTasks"
                :key="task.task_id"
                :label="`[${task.task_code}] ${task.equipment_name} (${task.equipment_code})`"
                :value="task.task_id"
              />
            </el-select>
          </el-col>
          <el-col :xs="24" :md="7">
            <div class="field-label">关联设备编号：</div>
            <el-input :value="currentTask?.equipment_code || '未关联'" disabled size="large" />
          </el-col>
          <el-col :xs="24" :md="7">
            <div class="field-label">截止日期：</div>
            <el-input :value="currentTask?.due_date || '当日'" disabled size="large" />
          </el-col>
        </el-row>
      </el-card>

      <!-- 巡检检查清单 (设备维护内容逐项判定 + SOP 比对) -->
      <div class="checklist-section">
        <div class="section-title">
          <span>设备维护内容清单 (共 {{ checklistItems.length }} 项)</span>
          <el-tag type="info">请戴手套逐一核对现场维护标准</el-tag>
        </div>

        <div class="items-list">
          <el-card
            v-for="(item, idx) in checklistItems"
            :key="item.plan_item_id"
            shadow="hover"
            class="inspection-item-card"
            :id="`item-card-${idx}`"
          >
            <!-- 检查项信息与 SOP 对比 -->
            <Checklist :item="item" :index="idx" />

            <!-- 48px+ 工控触摸判断按钮组 -->
            <div class="decision-box">
              <div class="touch-judge-group">
                <button
                  type="button"
                  class="touch-judge-btn pass"
                  :class="{ active: item.is_normal === true }"
                  @click="setItemNormal(item, true)"
                >
                  <el-icon :size="22" style="margin-right: 8px;"><Check /></el-icon>
                  正 常 (Pass)
                </button>

                <button
                  type="button"
                  class="touch-judge-btn fail"
                  :class="{ active: item.is_normal === false }"
                  @click="setItemNormal(item, false, idx)"
                >
                  <el-icon :size="22" style="margin-right: 8px;"><Close /></el-icon>
                  异 常 (Fail - 提报联锁)
                </button>
              </div>
            </div>

            <!-- 异常联动：强制要求上传现场证据照片与描述 (SWR-MNT-008) -->
            <div v-if="item.is_normal === false" class="anomaly-required-section">
              <el-alert
                title="已判定为异常：系统将原子级自动生成维修故障单，并将设备状态跃迁至【故障】！必须上传现场拍照证据。"
                type="error"
                :closable="false"
                show-icon
                style="margin-bottom: 12px;"
              />

              <el-form label-position="top">
                <el-form-item label="现场异常现象描述 (必填)" required>
                  <el-input
                    v-model="item.anomaly_desc"
                    type="textarea"
                    :rows="2"
                    placeholder="详细描述缺陷特征，如：轴承剧烈异响、油封漏油、压力表指针失灵等"
                  />
                </el-form-item>

                <el-form-item label="现场高清证据拍照/照片 (必填)" required>
                  <div class="photo-uploader-box">
                    <input
                      type="file"
                      accept="image/*"
                      :id="`upload-${idx}`"
                      style="display: none;"
                      @change="(e) => handleUploadPhoto(e, item)"
                    />
                    <el-button
                      type="warning"
                      size="large"
                      class="photo-btn"
                      :loading="item.uploading"
                      @click="triggerUpload(idx)"
                    >
                      <el-icon :size="20"><Camera /></el-icon>
                      <span>{{ item.evidence_file_id ? '照片已上传 (点击重拍)' : '现场拍照上传' }}</span>
                    </el-button>

                    <span v-if="item.evidence_file_id" class="upload-success-badge">
                      <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
                      文件ID: {{ item.evidence_file_id }}
                    </span>
                  </div>
                </el-form-item>
              </el-form>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 总体备注与底栏提交 (支持技术员上传完工工作凭证) -->
      <el-card shadow="never" class="remarks-card">
        <el-row :gutter="16">
          <el-col :xs="24" :md="16">
            <div class="field-label">维护总体备注 / 现场环境状况：</div>
            <el-input
              v-model="overallRemarks"
              type="textarea"
              :rows="3"
              placeholder="录入现场维护说明、环境温湿度、设备清洁度或其他备注信息..."
            />
          </el-col>
          <el-col :xs="24" :md="8">
            <div class="field-label">维护工作完成证据照片 (可选)：</div>
            <div class="completion-photo-box">
              <input
                type="file"
                accept="image/*"
                id="upload-completion-proof"
                style="display: none;"
                @change="handleUploadCompletionPhoto"
              />
              <el-button
                type="info"
                plain
                size="large"
                class="photo-btn"
                :loading="uploadingCompletionProof"
                @click="triggerCompletionUpload"
              >
                <el-icon :size="20"><Camera /></el-icon>
                <span>{{ completionProofFileId ? '完工凭证已上传 (重选)' : '拍摄/上传完工证据' }}</span>
              </el-button>
              <div v-if="completionProofFileId" class="upload-success-badge" style="margin-top: 6px;">
                <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
                凭证文件ID: {{ completionProofFileId }}
              </div>
            </div>
          </el-col>
        </el-row>

        <div class="submit-action-row">
          <el-button
            type="primary"
            size="large"
            :loading="submitting"
            class="submit-large-btn"
            @click="submitInspection"
          >
            确认并原子提交维护记录 (SWR-MNT-008)
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- ==================== 模式二：设备运行工时每日填报 ==================== -->
    <div v-else class="meter-mode-container">
      <!-- 统计指标看板 -->
      <el-row :gutter="16" class="meter-metrics-row">
        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="metric-card">
            <div class="metric-content">
              <div class="metric-icon total">
                <el-icon :size="28"><Cpu /></el-icon>
              </div>
              <div class="metric-data">
                <span class="metric-label">工时监控设备总数</span>
                <span class="metric-value">{{ operatingSummaries.length }} <small>台</small></span>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="metric-card">
            <div class="metric-content">
              <div class="metric-icon warning">
                <el-icon :size="28"><Warning /></el-icon>
              </div>
              <div class="metric-data">
                <span class="metric-label">达标预警 / 待维保机台</span>
                <span class="metric-value warning-text">{{ warningCount }} <small>台</small></span>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="metric-card">
            <div class="metric-content">
              <div class="metric-icon today">
                <el-icon :size="28"><Clock /></el-icon>
              </div>
              <div class="metric-data">
                <span class="metric-label">今日已填报机台</span>
                <span class="metric-value success-text">{{ todayLoggedCount }} <small>台</small></span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 工时填报主卡片与机台监控列表 -->
      <el-row :gutter="16">
        <!-- 左侧：快捷填报卡片 -->
        <el-col :xs="24" :lg="9">
          <el-card shadow="never" class="meter-form-card">
            <template #header>
              <div class="card-header-title">
                <el-icon :size="18" color="#409eff"><EditPen /></el-icon>
                <span>每日运行工时打卡</span>
              </div>
            </template>

            <el-form label-position="top" :model="meterForm">
              <el-form-item label="选择目标机台 (支持按编码/名称搜索)" required>
                <el-select
                  v-model="meterForm.equipment_id"
                  filterable
                  placeholder="请选择需填报的设备"
                  size="large"
                  style="width: 100%;"
                  @change="handleMeterEquipmentChange"
                >
                  <el-option
                    v-for="item in operatingSummaries"
                    :key="item.equipment_id"
                    :label="`[${item.equipment_code}] ${item.equipment_name}`"
                    :value="item.equipment_id"
                  >
                    <span style="float: left;">[{{ item.equipment_code }}] {{ item.equipment_name }}</span>
                    <span style="float: right; color: #8492a6; font-size: 13px;">
                      {{ item.current_operating_hours }}/{{ item.interval_hours }}h
                    </span>
                  </el-option>
                </el-select>
              </el-form-item>

              <!-- 当前选中机台运行态势 -->
              <div v-if="selectedEquipmentSummary" class="selected-eq-status-box">
                <div class="eq-status-title">
                  <strong>{{ selectedEquipmentSummary.equipment_name }}</strong>
                  <el-tag
                    size="small"
                    :type="selectedEquipmentSummary.is_due ? 'danger' : (selectedEquipmentSummary.is_warning ? 'warning' : 'success')"
                  >
                    {{ selectedEquipmentSummary.is_due ? '需立即维保' : (selectedEquipmentSummary.is_warning ? '临界预警中' : '运行正常') }}
                  </el-tag>
                </div>
                <div class="eq-progress-row">
                  <span>当前累计工时：<strong>{{ selectedEquipmentSummary.current_operating_hours }}</strong> / {{ selectedEquipmentSummary.interval_hours }} 小时</span>
                  <span>剩余：<strong :style="{ color: selectedEquipmentSummary.remaining_hours <= selectedEquipmentSummary.advance_warning_hours ? '#e6a23c' : '#67c23a' }">{{ selectedEquipmentSummary.remaining_hours }}h</strong></span>
                </div>
                <el-progress
                  :percentage="selectedEquipmentSummary.progress_percentage"
                  :status="selectedEquipmentSummary.is_due ? 'exception' : (selectedEquipmentSummary.is_warning ? 'warning' : 'success')"
                  :stroke-width="10"
                  style="margin-top: 6px;"
                />
              </div>

              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="工时发生日期" required>
                    <el-date-picker
                      v-model="meterForm.log_date"
                      type="date"
                      value-format="YYYY-MM-DD"
                      placeholder="选择日期"
                      size="large"
                      style="width: 100%;"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="当日开机运行工时 (h)" required>
                    <el-input-number
                      v-model="meterForm.duration_hours"
                      :min="0.5"
                      :max="24.0"
                      :step="0.5"
                      :precision="1"
                      size="large"
                      style="width: 100%;"
                    />
                  </el-form-item>
                </el-col>
              </el-row>

              <!-- 快捷工时预设按钮组 -->
              <div class="quick-hours-group">
                <span class="quick-title">班次快捷填充：</span>
                <el-button-group>
                  <el-button size="small" @click="meterForm.duration_hours = 4.0">+4h 半班</el-button>
                  <el-button size="small" type="primary" plain @click="meterForm.duration_hours = 8.0">+8h 单班制</el-button>
                  <el-button size="small" @click="meterForm.duration_hours = 12.0">+12h 加长班</el-button>
                  <el-button size="small" @click="meterForm.duration_hours = 16.0">+16h 两班倒</el-button>
                </el-button-group>
              </div>

              <el-form-item label="运行工况说明 / 生产批次备注" style="margin-top: 14px;">
                <el-input
                  v-model="meterForm.remarks"
                  type="textarea"
                  :rows="2"
                  placeholder="如: 白班正常生产运转、间歇试机运转4小时等..."
                />
              </el-form-item>

              <div class="submit-meter-action">
                <el-button
                  type="primary"
                  size="large"
                  :loading="submittingMeter"
                  class="submit-meter-btn"
                  @click="submitOperatingHours"
                >
                  <el-icon><Check /></el-icon> 确认录入当日工时 (自动检测预警)
                </el-button>
              </div>
            </el-form>
          </el-card>
        </el-col>

        <!-- 右侧：设备工时状态列表与历史流水 -->
        <el-col :xs="24" :lg="15">
          <el-card shadow="never" class="meter-list-card">
            <template #header>
              <div class="list-card-header">
                <div class="header-left">
                  <span class="card-title">各机台维保周期工时态势</span>
                  <el-radio-group v-model="filterWarningOnly" size="small" style="margin-left: 12px;">
                    <el-radio-button :value="false">全部设备 ({{ operatingSummaries.length }})</el-radio-button>
                    <el-radio-button :value="true">需维保/预警 ({{ warningCount }})</el-radio-button>
                  </el-radio-group>
                </div>
                <el-input
                  v-model="meterSearchKeyword"
                  placeholder="搜索机台名称/编码"
                  clearable
                  size="small"
                  style="width: 180px;"
                >
                  <template #prefix><el-icon><Search /></el-icon></template>
                </el-input>
              </div>
            </template>

            <el-table
              :data="filteredOperatingSummaries"
              v-loading="loadingOverview"
              border
              stripe
              style="width: 100%;"
            >
              <el-table-column prop="equipment_code" label="设备编码" width="120" />
              <el-table-column prop="equipment_name" label="设备名称" min-width="140" />
              <el-table-column label="工时进度 (累计 / 周期)" min-width="190">
                <template #default="{ row }">
                  <div class="table-progress-cell">
                    <div class="progress-labels">
                      <span class="hours-now">{{ row.current_operating_hours }}h</span>
                      <span class="hours-target">/ {{ row.interval_hours }}h</span>
                    </div>
                    <el-progress
                      :percentage="row.progress_percentage"
                      :status="row.is_due ? 'exception' : (row.is_warning ? 'warning' : 'success')"
                      :stroke-width="8"
                    />
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="剩余工时" width="105">
                <template #default="{ row }">
                  <span :style="{ color: row.remaining_hours <= row.advance_warning_hours ? '#e6a23c' : '#606266', fontWeight: 600 }">
                    {{ row.remaining_hours }} 小时
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="维保预警态势" width="120">
                <template #default="{ row }">
                  <el-tag
                    v-if="row.is_due"
                    type="danger"
                    effect="dark"
                    size="small"
                  >
                    需立即维保
                  </el-tag>
                  <el-tag
                    v-else-if="row.is_warning"
                    type="warning"
                    effect="dark"
                    size="small"
                  >
                    临界预警 (≤{{ row.advance_warning_hours }}h)
                  </el-tag>
                  <el-tag
                    v-else
                    type="success"
                    effect="plain"
                    size="small"
                  >
                    正常运转
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button
                    type="primary"
                    link
                    size="small"
                    @click="quickSelectEquipment(row)"
                  >
                    填工时
                  </el-button>
                  <el-button
                    type="info"
                    link
                    size="small"
                    @click="viewOperatingLogs(row)"
                  >
                    流水
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 设备运行工时流水抽屉/弹窗 -->
    <el-drawer
      v-model="logsDrawerVisible"
      :title="`机台 [${currentDrawerEq?.equipment_code}] ${currentDrawerEq?.equipment_name} · 运行工时填报明细`"
      size="600px"
    >
      <div v-loading="loadingLogs" class="logs-drawer-content">
        <div v-if="currentDrawerEq" class="drawer-summary-badge">
          <span>当前维保周期累计工时：<strong>{{ currentDrawerEq.current_operating_hours }}</strong> / {{ currentDrawerEq.interval_hours }} 小时</span>
          <el-tag :type="currentDrawerEq.is_due ? 'danger' : (currentDrawerEq.is_warning ? 'warning' : 'success')">
            {{ currentDrawerEq.is_due ? '已达维护工时' : (currentDrawerEq.is_warning ? '提前预警中' : '正常') }}
          </el-tag>
        </div>

        <el-table :data="currentEqLogs" border stripe style="width: 100%; margin-top: 14px;">
          <el-table-column prop="log_date" label="填报日期" width="115" />
          <el-table-column prop="duration_hours" label="当日工时" width="95">
            <template #default="{ row }">
              <strong>+{{ row.duration_hours }}h</strong>
            </template>
          </el-table-column>
          <el-table-column prop="cumulative_hours" label="累计工时" width="105">
            <template #default="{ row }">
              <span>{{ row.cumulative_hours }}h</span>
            </template>
          </el-table-column>
          <el-table-column prop="operator_name" label="填报人员" width="100" />
          <el-table-column prop="remarks" label="工况/批次说明" min-width="120">
            <template #default="{ row }">
              <span>{{ row.remarks || '无' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import apiClient from '@/api/client';
import Checklist from '@/components/Checklist.vue';
import {
  Check,
  Close,
  Camera,
  CircleCheckFilled,
  DocumentChecked,
  Timer,
  Warning,
  Clock,
  Cpu,
  EditPen,
  Search,
  Refresh,
} from '@element-plus/icons-vue';

// 模式切换：inspection (现场维护单) | meter (工时填报)
const activeMode = ref<'inspection' | 'meter'>('inspection');

// ==========================================
// 模式一：现场维护单状态
// ==========================================
interface InspectionItemState {
  plan_item_id: number;
  item_name: string;
  is_required: boolean;
  criteria?: string;
  method?: string;
  standard_photo_url?: string;
  is_normal: boolean | null;
  anomaly_desc?: string;
  evidence_file_id?: number | null;
  uploading?: boolean;
}

const myTasks = ref<any[]>([]);
const selectedTaskId = ref<number | null>(null);
const overallRemarks = ref('');
const submitting = ref(false);
const executionStartTime = ref<string>(new Date().toISOString());
const completionProofFileId = ref<number | null>(null);
const uploadingCompletionProof = ref(false);

const currentTask = computed(() => {
  return myTasks.value.find((t) => t.task_id === selectedTaskId.value) || null;
});

const defaultChecklist: InspectionItemState[] = [
  {
    plan_item_id: 1,
    item_name: '电机轴承振动与温升检测',
    is_required: true,
    criteria: '轴承振动速度有效值 RMS ≤ 2.8 mm/s，轴承外壳温升 ≤ 40℃',
    method: '采用点温枪与测振仪贴合电机驱动端及非驱动端测点',
    standard_photo_url: '',
    is_normal: null,
    anomaly_desc: '',
    evidence_file_id: null,
  },
  {
    plan_item_id: 2,
    item_name: '进出风管道密封性及异响排查',
    is_required: true,
    criteria: '法兰连接密封垫完好无冲刷痕迹，听诊无气蚀或叶轮刮擦破音声',
    method: '目视检查各连接法兰，结合听音棒于机壳中心排查',
    standard_photo_url: '',
    is_normal: null,
    anomaly_desc: '',
    evidence_file_id: null,
  },
  {
    plan_item_id: 3,
    item_name: 'PLC控制柜散热滤网与指示灯状态',
    is_required: false,
    criteria: '滤网积灰无结块堵塞，RUN绿色指示灯常亮，ERR红色指示灯熄灭',
    method: '打开控制柜前门检查指示状态及滤网透光度',
    standard_photo_url: '',
    is_normal: null,
    anomaly_desc: '',
    evidence_file_id: null,
  },
];

const checklistItems = ref<InspectionItemState[]>([...defaultChecklist]);

const setItemNormal = (item: InspectionItemState, val: boolean, idx?: number) => {
  item.is_normal = val;
  if (val) {
    item.anomaly_desc = '';
    item.evidence_file_id = null;
  } else if (idx !== undefined) {
    setTimeout(() => {
      const el = document.getElementById(`item-card-${idx}`);
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  }
};

const triggerUpload = (idx: number) => {
  const input = document.getElementById(`upload-${idx}`) as HTMLInputElement;
  input?.click();
};

const handleUploadPhoto = async (e: Event, item: InspectionItemState) => {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('file_tag', 'INSPECTION_PHOTO');

  item.uploading = true;
  try {
    const res = await apiClient.post<any, any>('/system/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    if (res.code === 200 && res.data) {
      item.evidence_file_id = res.data.file_id;
      ElMessage.success('现场照片上传并固化成功');
    }
  } catch (err) {
    console.error('File upload failed', err);
  } finally {
    item.uploading = false;
  }
};

const triggerCompletionUpload = () => {
  const input = document.getElementById('upload-completion-proof') as HTMLInputElement;
  input?.click();
};

const handleUploadCompletionPhoto = async (e: Event) => {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('file_tag', 'COMPLETION_PHOTO');

  uploadingCompletionProof.value = true;
  try {
    const res = await apiClient.post<any, any>('/system/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    if (res.code === 200 && res.data) {
      completionProofFileId.value = res.data.file_id;
      ElMessage.success('完工凭证照片上传成功');
    }
  } catch (err) {
    console.error('Completion file upload failed', err);
  } finally {
    uploadingCompletionProof.value = false;
  }
};

const handleTaskChange = () => {
  executionStartTime.value = new Date().toISOString();
  checklistItems.value.forEach((it) => {
    it.is_normal = null;
    it.anomaly_desc = '';
    it.evidence_file_id = null;
  });
  completionProofFileId.value = null;
};

const resetForm = () => {
  handleTaskChange();
  overallRemarks.value = '';
};

const fetchMyTasks = async () => {
  try {
    const res = await apiClient.get<any, any>('/maintenance/my-tasks');
    if (res.code === 200 && res.data && res.data.length > 0) {
      myTasks.value = res.data;
      selectedTaskId.value = res.data[0].task_id;
    }
  } catch (err) {
    console.error('Failed to load tasks', err);
  }
};

const submitInspection = async () => {
  for (let i = 0; i < checklistItems.value.length; i++) {
    const it = checklistItems.value[i];
    if (it.is_normal === null) {
      ElMessage.warning(`请先完成第 ${i + 1} 项【${it.item_name}】的判定`);
      return;
    }
    if (it.is_normal === false) {
      if (!it.anomaly_desc || it.anomaly_desc.trim() === '') {
        ElMessage.warning(`第 ${i + 1} 项判定为异常，必须填写异常现象描述！`);
        return;
      }
      if (!it.evidence_file_id) {
        ElMessage.warning(`第 ${i + 1} 项判定为异常，必须拍照上传现场证据照片！`);
        return;
      }
    }
  }

  submitting.value = true;
  try {
    const payload = {
      task_id: selectedTaskId.value || undefined,
      equipment_id: currentTask.value ? currentTask.value.equipment_id : 1,
      execution_start_time: executionStartTime.value,
      execution_end_time: new Date().toISOString(),
      overall_remarks: overallRemarks.value,
      details: checklistItems.value.map((it) => ({
        plan_item_id: it.plan_item_id,
        check_item_name: it.item_name,
        is_normal: it.is_normal,
        anomaly_desc: it.anomaly_desc || null,
        evidence_file_id: it.evidence_file_id || null,
      })),
    };

    const res = await apiClient.post<any, any>('/maintenance/inspections/submit', payload);
    if (res.code === 200) {
      if (res.data?.has_anomaly) {
        await ElMessageBox.alert(
          `维护单记录已成功归档！由于检测到异常，单事务引擎已自动联锁生成抢修工单（故障单ID: ${res.data.interlocked_fault_id || '已生成'}），关联设备状态已同步置为【故障待修】！`,
          '维护异常联锁提单成功',
          { type: 'warning', confirmButtonText: '确定' }
        );
      } else {
        ElMessage.success('维护单打卡完成，全项合格！当前维保周期累计工时已自动归零重置。');
      }
      resetForm();
      fetchMyTasks();
      fetchOperatingOverview();
    }
  } catch (err: any) {
    console.error('Submit inspection failed:', err);
  } finally {
    submitting.value = false;
  }
};

// ==========================================
// 模式二：设备运行工时每日填报与态势监控
// ==========================================
const operatingSummaries = ref<any[]>([]);
const loadingOverview = ref(false);
const filterWarningOnly = ref(false);
const meterSearchKeyword = ref('');
const submittingMeter = ref(false);

const getTodayString = () => {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const meterForm = reactive({
  equipment_id: null as number | null,
  log_date: getTodayString(),
  duration_hours: 8.0,
  remarks: '',
});

const selectedEquipmentSummary = computed(() => {
  if (!meterForm.equipment_id) return null;
  return operatingSummaries.value.find((s) => s.equipment_id === meterForm.equipment_id) || null;
});

const warningCount = computed(() => {
  return operatingSummaries.value.filter((s) => s.is_warning || s.is_due).length;
});

const todayLoggedCount = computed(() => {
  const todayStr = getTodayString();
  return operatingSummaries.value.filter((s) => s.last_log_date === todayStr).length;
});

const filteredOperatingSummaries = computed(() => {
  return operatingSummaries.value.filter((s) => {
    if (filterWarningOnly.value && !s.is_warning && !s.is_due) {
      return false;
    }
    if (meterSearchKeyword.value) {
      const kw = meterSearchKeyword.value.toLowerCase();
      const codeMatch = s.equipment_code?.toLowerCase().includes(kw);
      const nameMatch = s.equipment_name?.toLowerCase().includes(kw);
      return codeMatch || nameMatch;
    }
    return true;
  });
});

const fetchOperatingOverview = async () => {
  loadingOverview.value = true;
  try {
    const res = await apiClient.get<any, any>('/equipments/operating-overview/all');
    if (res.code === 200 && res.data) {
      operatingSummaries.value = res.data;
      if (!meterForm.equipment_id && res.data.length > 0) {
        meterForm.equipment_id = res.data[0].equipment_id;
      }
    }
  } catch (err) {
    console.error('Failed to load operating overview:', err);
  } finally {
    loadingOverview.value = false;
  }
};

const handleMeterEquipmentChange = (eqId: number) => {
  meterForm.equipment_id = eqId;
};

const quickSelectEquipment = (row: any) => {
  meterForm.equipment_id = row.equipment_id;
  ElMessage.info(`已选中机台：[${row.equipment_code}] ${row.equipment_name}，请录入工时`);
};

const submitOperatingHours = async () => {
  if (!meterForm.equipment_id) {
    ElMessage.warning('请先选择要填报工时的机台');
    return;
  }
  if (!meterForm.duration_hours || meterForm.duration_hours <= 0 || meterForm.duration_hours > 24) {
    ElMessage.warning('当日运行工时需在 0.1 至 24.0 小时之间');
    return;
  }

  submittingMeter.value = true;
  try {
    const payload = {
      equipment_id: meterForm.equipment_id,
      log_date: meterForm.log_date,
      duration_hours: meterForm.duration_hours,
      remarks: meterForm.remarks,
    };
    const res = await apiClient.post<any, any>(
      `/equipments/${meterForm.equipment_id}/operating-hours`,
      payload
    );
    if (res.code === 200) {
      const data = res.data;
      if (data?.triggered_maintenance) {
        await ElMessageBox.alert(
          `工时记录成功！累计工时达到 ${data.current_operating_hours}h，已达到或触发维护阈值！系统已自动生成维护工单并触发邮件通知维护主管！`,
          '维保预警触发通知',
          { type: 'warning', confirmButtonText: '已知悉' }
        );
      } else {
        ElMessage.success(`工时录入成功！当前累计运行工时: ${data.current_operating_hours} 小时`);
      }
      meterForm.remarks = '';
      fetchOperatingOverview();
    }
  } catch (err: any) {
    console.error('Submit operating hours error:', err);
  } finally {
    submittingMeter.value = false;
  }
};

// ==========================================
// 工时历史流水抽屉
// ==========================================
const logsDrawerVisible = ref(false);
const loadingLogs = ref(false);
const currentDrawerEq = ref<any>(null);
const currentEqLogs = ref<any[]>([]);

const viewOperatingLogs = async (eq: any) => {
  currentDrawerEq.value = eq;
  logsDrawerVisible.value = true;
  loadingLogs.value = true;
  try {
    const res = await apiClient.get<any, any>(`/equipments/${eq.equipment_id}/operating-logs?limit=50`);
    if (res.code === 200 && res.data) {
      currentEqLogs.value = res.data;
    }
  } catch (err) {
    console.error('Failed to load logs:', err);
  } finally {
    loadingLogs.value = false;
  }
};

onMounted(() => {
  fetchMyTasks();
  fetchOperatingOverview();
});
</script>

<style scoped>
.inspection-touch-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1300px;
  margin: 0 auto;
}

.touch-view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  padding: 16px 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-info h2 {
  margin: 0;
  font-size: 22px;
  color: #1e293b;
}

.sub-tip {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
  display: inline-block;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.submit-main-btn {
  height: 48px;
  padding: 0 28px;
  font-size: 16px;
  font-weight: 600;
}

.inspection-mode-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-selector-card {
  border-radius: 8px;
}

.field-label {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 6px;
}

.checklist-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: 700;
  color: #334155;
  padding: 0 4px;
}

.items-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.inspection-item-card {
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.decision-box {
  margin-top: 14px;
}

.touch-judge-group {
  display: flex;
  gap: 16px;
}

.touch-judge-btn {
  flex: 1;
  height: 64px;
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 2px solid #dcdfe6;
  background-color: #f8fafc;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.touch-judge-btn.pass.active {
  background-color: #dcfce7;
  border-color: #22c55e;
  color: #15803d;
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.25);
}

.touch-judge-btn.fail.active {
  background-color: #fee2e2;
  border-color: #ef4444;
  color: #b91c1c;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.25);
}

.anomaly-required-section {
  margin-top: 16px;
  padding: 18px;
  background-color: #fffaf0;
  border: 2px dashed #f59e0b;
  border-radius: 8px;
}

.photo-uploader-box, .completion-photo-box {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.photo-btn {
  height: 48px;
  padding: 0 20px;
  font-size: 15px;
  font-weight: 600;
}

.upload-success-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #16a34a;
  font-weight: 500;
}

.remarks-card {
  border-radius: 8px;
}

.submit-action-row {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.submit-large-btn {
  height: 52px;
  padding: 0 36px;
  font-size: 17px;
  font-weight: 700;
}

/* ==========================================
   模式二：工时填报样式
   ========================================== */
.meter-mode-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.meter-metrics-row {
  margin-bottom: 4px;
}

.metric-card {
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.metric-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.metric-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon.total {
  background: #eff6ff;
  color: #3b82f6;
}

.metric-icon.warning {
  background: #fffbeb;
  color: #f59e0b;
}

.metric-icon.today {
  background: #f0fdf4;
  color: #10b981;
}

.metric-data {
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 13px;
  color: #64748b;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
}

.metric-value small {
  font-size: 14px;
  font-weight: normal;
  color: #94a3b8;
}

.warning-text {
  color: #f59e0b !important;
}

.success-text {
  color: #10b981 !important;
}

.meter-form-card, .meter-list-card {
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.card-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.selected-eq-status-box {
  background: #f8fafc;
  padding: 12px 14px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  margin-bottom: 14px;
}

.eq-status-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.eq-progress-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #64748b;
  margin-bottom: 4px;
}

.quick-hours-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: 4px 0 10px 0;
}

.quick-title {
  font-size: 13px;
  color: #64748b;
}

.submit-meter-action {
  margin-top: 18px;
}

.submit-meter-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
}

.list-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.header-left {
  display: flex;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.table-progress-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.progress-labels {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-size: 12px;
}

.hours-now {
  font-weight: 700;
  color: #1e293b;
}

.hours-target {
  color: #94a3b8;
}

.drawer-summary-badge {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f1f5f9;
  border-radius: 6px;
}
</style>
