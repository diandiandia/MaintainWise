<template>
  <div class="maintenance-view">
    <div class="page-header">
      <div class="header-titles">
        <h2>维保计划编制与执行监控</h2>
        <p>支持周期策略配置、SOP 清单维护、版本升级快照固化及任务派单 (SWR-MNT-001/003/004)</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Download" @click="exportInspectionReport">导出全量巡检报表</el-button>
        <el-button v-permission="['ADMIN', 'ENGINEER']" type="primary" :icon="Plus" @click="openPlanDialog">编制新维护计划</el-button>
      </div>
    </div>

    <!-- 标签页切换：维护计划 / 待办工单 / 完成率报表 -->
    <el-card shadow="never" class="main-card">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 计划列表 -->
        <el-tab-pane label="维保计划策略" name="plans">
          <el-table :data="plans" v-loading="loading" border stripe>
            <el-table-column prop="plan_code" label="计划编码" width="140" />
            <el-table-column prop="plan_name" label="计划名称" min-width="160" />
            <el-table-column prop="version" label="当前版本" width="100">
              <template #default="{ row }">
                <el-tag size="small" type="warning">v{{ row.version }}.0</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="interval_hours" label="维护周期" width="120">
              <template #default="{ row }">
                {{ row.interval_hours }} 小时（{{ (row.interval_hours / 24).toFixed(1) }}天）
              </template>
            </el-table-column>
            <el-table-column prop="advance_notice_days" label="提前预警" width="100">
              <template #default="{ row }">
                {{ row.advance_notice_days }} 天
              </template>
            </el-table-column>
            <el-table-column prop="is_active" label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? '启用中' : '已停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-permission="['ADMIN', 'ENGINEER']"
                  type="primary"
                  link
                  size="small"
                  @click="handleBumpVersion(row)"
                >
                  升级版本快照
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 到期任务 -->
        <el-tab-pane label="执行中维护工单" name="tasks">
          <el-table :data="tasks" v-loading="loading" border stripe>
            <el-table-column prop="task_code" label="任务工单号" width="160" />
            <el-table-column prop="equipment_name" label="所属设备" min-width="160">
              <template #default="{ row }">
                {{ row.equipment_name }} ({{ row.equipment_code }})
              </template>
            </el-table-column>
            <el-table-column prop="due_date" label="截止日期" width="130" />
            <el-table-column prop="status" label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="row.status === 'OVERDUE' ? 'danger' : 'warning'">
                  {{ row.status === 'OVERDUE' ? '已超期' : '待巡检' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button
                  type="success"
                  size="small"
                  @click="$router.push('/inspection')"
                >
                  现场打卡
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 完成率大盘统计 (SWR-MNT-010) -->
        <el-tab-pane label="维保履约完成率统计" name="rate">
          <div class="completion-rate-box">
            <el-table :data="completionRates" border stripe>
              <el-table-column prop="dimension_name" label="统计维度 / 班组工种" min-width="150" />
              <el-table-column prop="total_due" label="应检工单总数" width="140" />
              <el-table-column prop="completed_on_time" label="按期完成数" width="140" />
              <el-table-column label="按期履约完成率" width="220">
                <template #default="{ row }">
                  <el-progress
                    :percentage="Math.round(row.rate_percentage)"
                    :status="row.rate_percentage >= 90 ? 'success' : 'warning'"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 编制维护计划弹窗 (SWR-MNT-001) -->
    <el-dialog
      v-model="planDialogVisible"
      title="编制设备预防性维护计划与SOP标准"
      width="720px"
      append-to-body
    >
      <el-form ref="planFormRef" :model="planForm" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="计划名称" required>
              <el-input v-model="planForm.plan_name" placeholder="如: 主风机月度深度维保" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="关联设备（工厂 → 部门 → 系统 → 设备）" required>
              <el-cascader
                v-model="planForm.selectedEquipmentPaths"
                :options="equipmentTreeOptions"
                :props="{ label: 'label', value: 'value', children: 'children', multiple: true, checkStrictly: false }"
                placeholder="请选择设备，支持多选"
                clearable
                collapse-tags
                collapse-tags-tooltip
                style="width: 100%;"
                @change="handleEquipmentSelect"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="维护周期（小时）" required>
              <el-input-number v-model="planForm.interval_hours" :min="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="等效天数（参考）">
              <el-input :value="(planForm.interval_hours / 24).toFixed(1) + ' 天'" readonly style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="提前预警天数">
              <el-input-number v-model="planForm.advance_notice_days" :min="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 设备维护内容 (SWR-MNT-002) -->
        <el-divider content-position="left">设备维护内容</el-divider>

        <div v-for="(it, idx) in planForm.items" :key="idx" class="plan-item-row">
          <el-row :gutter="10">
            <el-col :span="10">
              <el-input v-model="it.check_item_name" placeholder="检查项目名称" />
            </el-col>
            <el-col :span="10">
              <el-input v-model="it.standard_benchmark" placeholder="判定标准指标" />
            </el-col>
            <el-col :span="4">
              <el-switch v-model="it.is_required" active-text="必检" />
            </el-col>
          </el-row>
        </div>

        <el-button type="primary" link :icon="Plus" @click="addPlanItem">增加维护项</el-button>
      </el-form>

      <template #footer>
        <el-button @click="planDialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="savingPlan" @click="submitPlan">保存维护计划</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import apiClient from '@/api/client';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Download } from '@element-plus/icons-vue';

const activeTab = ref('plans');
const loading = ref(false);
const plans = ref<any[]>([]);
const tasks = ref<any[]>([]);
const completionRates = ref<any[]>([]);

const planDialogVisible = ref(false);
const savingPlan = ref(false);

const planForm = reactive({
  plan_name: '',
  equipment_ids: [] as number[],
  selectedEquipmentPaths: [] as any[],
  interval_hours: 720,
  advance_notice_days: 3,
  items: [
    { item_order: 1, check_item_name: '轴承润滑油位与油质', standard_benchmark: '油位处于油标1/2至2/3处，无乳化', is_required: true },
    { item_order: 2, check_item_name: '叶轮动平衡与紧固件', standard_benchmark: '锁紧螺母防松铁丝完好，叶片无积灰偏重', is_required: true },
  ],
});

const equipmentTreeOptions = ref<any[]>([]);

// 将位置树转换为 el-cascader 所需的格式
const transformTreeForCascader = (nodes: any[]): any[] => {
  return nodes.map((node: any) => {
    const isEquipment = node.node_type === 'EQUIPMENT';
    const transformed: any = {
      value: isEquipment ? `eq_${node.equipment_id}` : `loc_${node.id}`,
      label: node.location_name,
      equipment_id: isEquipment ? node.equipment_id : undefined,
    };
    if (node.children && node.children.length > 0) {
      transformed.children = transformTreeForCascader(node.children);
    }
    return transformed;
  });
};

// 加载设备树（含设备节点）
const fetchEquipmentTree = async () => {
  try {
    const res = await apiClient.get<any, any>('/locations/tree?include_equipments=true');
    if (res.code === 200 && res.data) {
      equipmentTreeOptions.value = transformTreeForCascader(res.data);
    }
  } catch (err) {
    console.error('加载设备树失败:', err);
  }
};

// 级联选择变化时，提取设备ID列表
const handleEquipmentSelect = (values: any) => {
  // values 是二维数组，如 [["loc_1", "loc_2", "loc_3", "eq_1"], ["loc_1", "loc_2", "loc_3", "eq_2"]]
  // 提取每个路径的最后一个元素，即设备节点
  const eqIds: number[] = [];
  if (values && Array.isArray(values)) {
    for (const path of values) {
      if (Array.isArray(path) && path.length > 0) {
        const last = path[path.length - 1];
        if (typeof last === 'string' && last.startsWith('eq_')) {
          const eqId = parseInt(last.replace('eq_', ''), 10);
          if (!isNaN(eqId)) {
            eqIds.push(eqId);
          }
        }
      }
    }
  }
  planForm.equipment_ids = eqIds;
};

const getIntervalUnit = (u?: string) => {
  switch (u) {
    case 'DAYS': return '天';
    case 'WEEKS': return '周';
    case 'MONTHS': return '月';
    default: return u || '';
  }
};

const addPlanItem = () => {
  planForm.items.push({
    item_order: planForm.items.length + 1,
    check_item_name: '',
    standard_benchmark: '',
    is_required: true,
  });
};

const handleTabChange = (tab: any) => {
  if (tab === 'plans') fetchPlans();
  else if (tab === 'tasks') fetchTasks();
  else if (tab === 'rate') fetchCompletionRate();
};

const fetchPlans = async () => {
  loading.value = true;
  try {
    const res = await apiClient.get<any, any>('/maintenance/plans');
    if (res.code === 200 && res.data) {
      plans.value = res.data;
    }
  } catch (err) {
    console.error(err);
  } finally {
    loading.value = false;
  }
};

const fetchTasks = async () => {
  loading.value = true;
  try {
    const res = await apiClient.get<any, any>('/maintenance/my-tasks');
    if (res.code === 200 && res.data) {
      tasks.value = res.data;
    }
  } catch (err) {
    console.error(err);
  } finally {
    loading.value = false;
  }
};

const fetchCompletionRate = async () => {
  try {
    const res = await apiClient.get<any, any>('/maintenance/statistics/completion-rate');
    if (res.code === 200 && res.data) {
      completionRates.value = res.data;
    }
  } catch (err) {
    console.error(err);
  }
};

const handleBumpVersion = async (plan: any) => {
  try {
    await ElMessageBox.confirm(`确认将维护计划【${plan.plan_name}】升级至下一版本并固化历史快照？`, '版本快照升级', { type: 'warning' });
    const res = await apiClient.put<any, any>(`/maintenance/plans/${plan.id}/bump-version`);
    if (res.code === 200) {
      ElMessage.success('计划版本升级成功，旧版本已安全固化');
      fetchPlans();
    }
  } catch (err) {
    // Cancelled
  }
};

const openPlanDialog = () => {
  planForm.plan_name = '';
  planForm.equipment_ids = [];
  planForm.selectedEquipmentPaths = [];
  planForm.interval_hours = 720;
  planForm.advance_notice_days = 3;
  planForm.items = [
    { item_order: 1, check_item_name: '轴承润滑油位与油质', standard_benchmark: '油位处于油标1/2至2/3处，无乳化', is_required: true },
    { item_order: 2, check_item_name: '叶轮动平衡与紧固件', standard_benchmark: '锁紧螺母防松铁丝完好，叶片无积灰偏重', is_required: true },
  ];
  fetchEquipmentTree();
  planDialogVisible.value = true;
};

const submitPlan = async () => {
  if (!planForm.plan_name) {
    ElMessage.warning('请输入计划名称');
    return;
  }
  if (!planForm.equipment_ids || planForm.equipment_ids.length === 0) {
    ElMessage.warning('请至少选择一台关联设备');
    return;
  }
  savingPlan.value = true;
  try {
    const payload = {
      plan_name: planForm.plan_name,
      plan_code: 'PLAN-' + Date.now(),
      plan_type: 'MONTHLY',
      interval_hours: planForm.interval_hours,
      interval_days: Math.ceil(planForm.interval_hours / 24),
      advance_notice_days: planForm.advance_notice_days,
      sop_content: planForm.plan_name + ' 标准维护流程',
      equipment_ids: planForm.equipment_ids,
      items: planForm.items.map((it, idx) => ({
        item_order: idx + 1,
        check_item_name: it.check_item_name,
        standard_benchmark: it.standard_benchmark,
        is_required: it.is_required,
      })),
    };
    const res = await apiClient.post<any, any>('/maintenance/plans', payload);
    if (res.code === 200) {
      ElMessage.success('维护计划编制成功');
      planDialogVisible.value = false;
      fetchPlans();
    }
  } catch (err) {
    console.error(err);
  } finally {
    savingPlan.value = false;
  }
};

const exportInspectionReport = () => {
  window.open('/api/v1/maintenance/inspections/export/excel', '_blank');
};

onMounted(() => {
  fetchPlans();
});
</script>

<style scoped>
.maintenance-view {
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

.main-card {
  min-height: calc(100vh - 200px);
}

.plan-item-row {
  margin-bottom: 10px;
  background: #f8fafc;
  padding: 8px 12px;
  border-radius: 6px;
}

.completion-rate-box {
  max-width: 800px;
  margin-top: 10px;
}
</style>