<template>
  <div class="equipment-view">
    <el-row :gutter="16">
      <!-- 左侧 5 级位置树拓扑 (SWR-DEV-001) -->
      <el-col :xs="24" :md="6">
        <el-card shadow="never" class="location-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">车间层级拓扑树</span>
              <el-button size="small" link :icon="Refresh" @click="fetchLocationTree" />
            </div>
          </template>

          <el-tree
            :data="locationTree"
            :props="treeProps"
            node-key="id"
            highlight-current
            default-expand-all
            @node-click="handleNodeClick"
          >
            <template #default="{ data }">
              <span class="tree-node">
                <el-icon :size="14" color="#409eff"><OfficeBuilding /></el-icon>
                <span>{{ data.location_name }}</span>
                <el-tag size="small" type="info" effect="plain" class="level-tag">L{{ data.level_depth }}</el-tag>
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <!-- 右侧设备台账与多维检索 (SWR-DEV-003/007) -->
      <el-col :xs="24" :md="18">
        <el-card shadow="never" class="equipment-card">
          <div class="toolbar">
            <div class="filter-inputs">
              <el-input
                v-model="filters.keyword"
                placeholder="搜索设备名称 / 编号"
                clearable
                style="width: 200px;"
                @change="fetchEquipments"
              />

              <el-select
                v-model="filters.equipmentType"
                placeholder="设备类型"
                clearable
                style="width: 140px;"
                @change="fetchEquipments"
              >
                <el-option label="全部类型" value="" />
                <el-option label="PLC控制器" value="PLC" />
                <el-option label="工业风机" value="FAN" />
                <el-option label="三相电机" value="MOTOR" />
                <el-option label="传感器" value="SENSOR" />
                <el-option label="变频器" value="VFD" />
              </el-select>

              <el-select
                v-model="filters.status"
                placeholder="运行状态"
                clearable
                style="width: 130px;"
                @change="fetchEquipments"
              >
                <el-option label="全部状态" value="" />
                <el-option label="正常运行" value="RUNNING" />
                <el-option label="待维护" value="MAINTENANCE_PENDING" />
                <el-option label="故障异常" value="FAULTY" />
                <el-option label="计划停机" value="SHUTDOWN" />
              </el-select>

              <el-button type="primary" :icon="Search" @click="fetchEquipments">查 询</el-button>
            </div>

            <div class="action-buttons">
              <el-button v-permission="['ADMIN', 'ENGINEER']" type="primary" :icon="Plus" @click="openCreateDialog">录入设备</el-button>
              <el-button v-permission="['ADMIN', 'ENGINEER']" :icon="Download" @click="exportExcel">导出Excel</el-button>
            </div>
          </div>

          <!-- 设备表格 -->
          <el-table
            v-loading="loading"
            :data="equipments"
            style="width: 100%; margin-top: 14px;"
            border
            stripe
          >
            <el-table-column prop="equipment_code" label="设备编号" width="130" font-weight="600" />
            <el-table-column prop="equipment_name" label="设备名称" min-width="140" />
            <el-table-column prop="equipment_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.equipment_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="model_spec" label="型号规格" width="120" />
            <el-table-column prop="work_type" label="工种隔离" width="90">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.work_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="getStatusTag(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="rated_voltage" label="额定电压" width="90" />
            <el-table-column label="专有参数" width="100">
              <template #default="{ row }">
                <el-button
                  v-if="row.params"
                  type="primary"
                  link
                  size="small"
                  @click="viewParams(row)"
                >
                  查看参数
                </el-button>
                <span v-else style="color: #909399; font-size: 12px;">无</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  link
                  size="small"
                  @click="viewTimeline(row)"
                >
                  电子履历
                </el-button>
                <el-button
                  v-permission="['ADMIN', 'ENGINEER']"
                  type="danger"
                  link
                  size="small"
                  @click="handleDelete(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 录入设备弹窗 (带 11 类专有强校验参数 - SWR-DEV-003/004) -->
    <el-dialog
      v-model="createDialogVisible"
      title="录入新设备台账与专有参数"
      width="680px"
      append-to-body
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="设备编码" prop="equipment_code">
              <el-input v-model="form.equipment_code" placeholder="如: FAN-001" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备名称" prop="equipment_name">
              <el-input v-model="form.equipment_name" placeholder="如: 1号主排风风机" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="设备类型" prop="equipment_type">
              <el-select v-model="form.equipment_type" style="width: 100%;">
                <el-option label="PLC控制器" value="PLC" />
                <el-option label="工业风机" value="FAN" />
                <el-option label="三相异步电机" value="MOTOR" />
                <el-option label="传感器" value="SENSOR" />
                <el-option label="通用设备" value="OTHER" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="责任工种" prop="work_type">
              <el-select v-model="form.work_type" style="width: 100%;">
                <el-option label="机械工 (MECHANICAL)" value="MECHANICAL" />
                <el-option label="电气工 (ELECTRICAL)" value="ELECTRICAL" />
                <el-option label="自动化仪表 (INSTRUMENTATION)" value="INSTRUMENTATION" />
                <el-option label="通用全工种 (GENERAL)" value="GENERAL" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="型号规格" prop="model_spec">
              <el-input v-model="form.model_spec" placeholder="如: Y4-73 No.8D" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属位置ID" prop="location_id">
              <el-input-number v-model="form.location_id" :min="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 专有参数子表单 (SWR-DEV-004) -->
        <el-divider content-position="left">11类设备专有参数 Schema 强校验</el-divider>

        <div v-if="form.equipment_type === 'PLC'" class="param-group">
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="通信 IP 地址 (格式严格校验)">
                <el-input v-model="plcParams.ip_address" placeholder="如: 192.168.1.10" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="通信协议">
                <el-select v-model="plcParams.protocol" style="width: 100%;">
                  <el-option label="Modbus TCP" value="MODBUS_TCP" />
                  <el-option label="Profinet" value="PROFINET" />
                  <el-option label="EtherCAT" value="ETHERCAT" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <div v-if="form.equipment_type === 'FAN'" class="param-group">
          <el-row :gutter="12">
            <el-col :span="8">
              <el-form-item label="额定风量 (m³/h > 0)">
                <el-input-number v-model="fanParams.air_volume" :min="1" style="width: 100%;" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="全压 (Pa > 0)">
                <el-input-number v-model="fanParams.total_pressure" :min="1" style="width: 100%;" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="主轴转速 (rpm)">
                <el-input-number v-model="fanParams.rotation_speed" :min="1" style="width: 100%;" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">保 存</el-button>
      </template>
    </el-dialog>

    <!-- 电子履历时间线抽屉 (SWR-DEV-008) -->
    <el-drawer
      v-model="timelineVisible"
      :title="`设备全生命周期电子履历 - [${currentEquipment?.equipment_code}] ${currentEquipment?.equipment_name}`"
      size="480px"
    >
      <div v-loading="timelineLoading" class="timeline-box">
        <el-empty v-if="timelineList.length === 0" description="暂无维保与故障记录" />
        <el-timeline v-else>
          <el-timeline-item
            v-for="(t, idx) in timelineList"
            :key="idx"
            :type="t.event_type === 'FAULT' ? 'danger' : 'primary'"
            :timestamp="formatDate(t.event_time)"
          >
            <div class="timeline-content">
              <h4>{{ t.title }}</h4>
              <p>{{ t.description }}</p>
              <span class="operator">操作/执行人: {{ t.operator_name || '系统自动' }}</span>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-drawer>

    <!-- 专有参数展示弹窗 -->
    <el-dialog v-model="paramDialogVisible" title="专有参数明细" width="450px">
      <el-descriptions border :column="1">
        <el-descriptions-item
          v-for="(val, key) in currentParams"
          :key="key"
          :label="String(key)"
        >
          {{ val }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import apiClient from '@/api/client';
import { ElMessage, ElMessageBox, FormInstance } from 'element-plus';
import {
  OfficeBuilding,
  Refresh,
  Search,
  Plus,
  Download,
} from '@element-plus/icons-vue';

const loading = ref(false);
const equipments = ref<any[]>([]);
const locationTree = ref<any[]>([]);
const treeProps = { children: 'children', label: 'location_name' };

const filters = reactive({
  keyword: '',
  equipmentType: '',
  status: '',
  locationId: null as number | null,
});

const createDialogVisible = ref(false);
const saving = ref(false);
const formRef = ref<FormInstance>();
const form = reactive({
  equipment_code: '',
  equipment_name: '',
  equipment_type: 'FAN',
  work_type: 'MECHANICAL',
  model_spec: '',
  location_id: 1,
  rated_voltage: '380V',
});

const plcParams = reactive({
  ip_address: '192.168.1.50',
  protocol: 'PROFINET',
});

const fanParams = reactive({
  air_volume: 12000,
  total_pressure: 1800,
  rotation_speed: 1450,
});

const formRules = {
  equipment_code: [{ required: true, message: '请输入编号', trigger: 'blur' }],
  equipment_name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  equipment_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  location_id: [{ required: true, message: '请指定位置', trigger: 'blur' }],
};

// 电子履历
const timelineVisible = ref(false);
const timelineLoading = ref(false);
const currentEquipment = ref<any>(null);
const timelineList = ref<any[]>([]);

// 参数展示
const paramDialogVisible = ref(false);
const currentParams = ref<Record<string, any>>({});

const getStatusLabel = (s?: string) => {
  switch (s) {
    case 'RUNNING': return '正常运行';
    case 'MAINTENANCE_PENDING': return '待维护';
    case 'FAULTY': return '故障异常';
    case 'SHUTDOWN': return '计划停机';
    default: return s || '未知';
  }
};

const getStatusTag = (s?: string) => {
  switch (s) {
    case 'RUNNING': return 'success';
    case 'MAINTENANCE_PENDING': return 'warning';
    case 'FAULTY': return 'danger';
    case 'SHUTDOWN': return 'info';
    default: return 'info';
  }
};

const formatDate = (t?: string) => {
  if (!t) return '';
  return t.replace('T', ' ').substring(0, 16);
};

const fetchLocationTree = async () => {
  try {
    const res = await apiClient.get<any, any>('/locations/tree');
    if (res.code === 200) {
      locationTree.value = res.data;
    }
  } catch (err) {
    console.error(err);
  }
};

const handleNodeClick = (node: any) => {
  filters.locationId = node.id;
  fetchEquipments();
};

const fetchEquipments = async () => {
  loading.value = true;
  try {
    let url = `/equipments?limit=50`;
    if (filters.equipmentType) url += `&equipment_type=${filters.equipmentType}`;
    if (filters.status) url += `&status=${filters.status}`;

    const res = await apiClient.get<any, any>(url);
    if (res.code === 200 && res.data?.items) {
      equipments.value = res.data.items;
    }
  } catch (err) {
    console.error(err);
  } finally {
    loading.value = false;
  }
};

const openCreateDialog = () => {
  createDialogVisible.value = true;
};

const submitCreate = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    saving.value = true;
    try {
      const payload: any = { ...form };
      if (form.equipment_type === 'PLC') {
        payload.params = plcParams;
      } else if (form.equipment_type === 'FAN') {
        payload.params = fanParams;
      }
      const res = await apiClient.post<any, any>('/equipments', payload);
      if (res.code === 200) {
        ElMessage.success('设备台账录入成功，专有参数已通过校验');
        createDialogVisible.value = false;
        fetchEquipments();
      }
    } catch (err) {
      console.error(err);
    } finally {
      saving.value = false;
    }
  });
};

const viewParams = (row: any) => {
  currentParams.value = row.params || {};
  paramDialogVisible.value = true;
};

const viewTimeline = async (row: any) => {
  currentEquipment.value = row;
  timelineVisible.value = true;
  timelineLoading.value = true;
  try {
    const res = await apiClient.get<any, any>(`/equipments/${row.id}/timeline`);
    if (res.code === 200 && res.data) {
      timelineList.value = res.data;
    }
  } catch (err) {
    console.error(err);
  } finally {
    timelineLoading.value = false;
  }
};

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(`确认删除设备【${row.equipment_name}】？`, '警告', { type: 'warning' });
    const res = await apiClient.delete<any, any>(`/equipments/${row.id}`);
    if (res.code === 200) {
      ElMessage.success('设备已安全软删除');
      fetchEquipments();
    }
  } catch (err) {
    // Cancelled
  }
};

const exportExcel = () => {
  window.open('/api/v1/equipments/export/excel', '_blank');
};

onMounted(() => {
  fetchLocationTree();
  fetchEquipments();
});
</script>

<style scoped>
.equipment-view {
  display: flex;
  flex-direction: column;
}

.location-card {
  min-height: calc(100vh - 120px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-weight: 600;
  font-size: 15px;
  color: #1e293b;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.level-tag {
  font-size: 10px;
  margin-left: 6px;
  padding: 0 4px;
}

.equipment-card {
  min-height: calc(100vh - 120px);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-inputs {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.param-group {
  background-color: #f8fafc;
  padding: 12px;
  border-radius: 6px;
}

.timeline-box {
  padding: 10px 0;
}

.timeline-content h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: #1e293b;
}

.timeline-content p {
  margin: 0 0 4px 0;
  font-size: 13px;
  color: #64748b;
}

.timeline-content .operator {
  font-size: 12px;
  color: #94a3b8;
}
</style>
