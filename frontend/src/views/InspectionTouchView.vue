<template>
  <div class="inspection-touch-view">
    <!-- 顶部状态栏 -->
    <div class="touch-view-header">
      <div class="header-info">
        <h2>车间现场巡检打卡</h2>
        <span class="sub-tip">工控平板与防误触优化模式 (SWR-MNT-007 / SWR-NFR-005)</span>
      </div>
      <div class="header-actions">
        <el-button type="info" plain size="large" @click="resetForm">重 置</el-button>
        <el-button
          type="primary"
          size="large"
          :loading="submitting"
          class="submit-main-btn"
          @click="submitInspection"
        >
          提交打卡记录
        </el-button>
      </div>
    </div>

    <!-- 任务选择与设备信息卡片 -->
    <el-card shadow="never" class="task-selector-card">
      <el-row :gutter="16" align="middle">
        <el-col :xs="24" :md="10">
          <div class="field-label">当前待执行任务：</div>
          <el-select
            v-model="selectedTaskId"
            placeholder="请选择或扫码待巡检工单"
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

    <!-- 巡检检查清单 (逐项判定 + SOP 比对) -->
    <div class="checklist-section">
      <div class="section-title">
        <span>逐项判定清单 (共 {{ checklistItems.length }} 项)</span>
        <el-tag type="info">请戴手套逐一核对现场运行状态</el-tag>
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

    <!-- 总体备注与底栏提交 -->
    <el-card shadow="never" class="remarks-card">
      <div class="field-label">巡检总体备注 / 现场环境状况：</div>
      <el-input
        v-model="overallRemarks"
        type="textarea"
        :rows="2"
        placeholder="录入现场温湿度、设备清洁度或其他环境说明..."
      />
      <div class="submit-action-row">
        <el-button
          type="primary"
          size="large"
          :loading="submitting"
          class="submit-large-btn"
          @click="submitInspection"
        >
          确认并原子提交巡检记录 (SWR-MNT-008)
        </el-button>
      </div>
    </el-card>
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
} from '@element-plus/icons-vue';

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

const currentTask = computed(() => {
  return myTasks.value.find((t) => t.task_id === selectedTaskId.value) || null;
});

// 默认巡检项数据源
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
    // 自动平滑滚动至异常填写区
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

const handleTaskChange = () => {
  // 重置时间与判定
  executionStartTime.value = new Date().toISOString();
  checklistItems.value.forEach((it) => {
    it.is_normal = null;
    it.anomaly_desc = '';
    it.evidence_file_id = null;
  });
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
  // 1. 基础校验：必须全部完成判定
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
          `巡检记录已成功归档！由于检测到异常，单事务引擎已自动联锁生成抢修工单（故障单ID: ${res.data.interlocked_fault_id || '已生成'}），关联设备状态已同步置为【故障待修】！`,
          '巡检异常联锁提单成功',
          { type: 'warning', confirmButtonText: '查看故障单' }
        );
      } else {
        ElMessage.success('巡检打卡完成，全项合格，下一次巡检周期已自动排期！');
      }
      resetForm();
      fetchMyTasks();
    }
  } catch (err: any) {
    console.error('Submit inspection failed:', err);
  } finally {
    submitting.value = false;
  }
};

onMounted(() => {
  fetchMyTasks();
});
</script>

<style scoped>
.inspection-touch-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1200px;
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

.header-info h2 {
  margin: 0 0 4px 0;
  font-size: 22px;
  color: #1e293b;
}

.sub-tip {
  font-size: 13px;
  color: #64748b;
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

.photo-uploader-box {
  display: flex;
  align-items: center;
  gap: 16px;
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
</style>
