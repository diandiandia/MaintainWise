<template>
  <div class="equipment-view">
    <el-row :gutter="16">
      <!-- 左侧 4 级车间层级拓扑树 (工厂 -> 部门 -> 系统 -> 设备信息) -->
      <el-col :xs="24" :md="7">
        <el-card shadow="never" class="location-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">车间层级拓扑</span>
              <div class="header-tools">
                <el-dropdown v-if="authStore.isAdmin" trigger="click" @command="(cmd: string) => openAddLocation(Number(cmd))">
                  <el-button size="small" type="primary">
                    + 新建拓扑节点 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="1">🏭 新建工厂 (Level 1)</el-dropdown-item>
                      <el-dropdown-item command="2">🏢 新建部门 (Level 2)</el-dropdown-item>
                      <el-dropdown-item command="3">⚙️ 新建系统 (Level 3)</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-button size="small" link :icon="Refresh" @click="fetchLocationTree" />
              </div>
            </div>
          </template>

          <!-- 顶部快捷操作栏 (管理员可直接录入工厂/部门/系统/设备) -->
          <div v-if="authStore.isAdmin" class="quick-add-bar">
            <el-button size="small" type="primary" plain @click="openAddLocation(1)">+ 新建工厂</el-button>
            <el-button size="small" type="success" plain @click="openAddLocation(2)">+ 新建部门</el-button>
            <el-button size="small" type="warning" plain @click="openAddLocation(3)">+ 新建系统</el-button>
            <el-button size="small" type="primary" @click="openCreateDialog">+ 录入设备</el-button>
          </div>

          <!-- 层级结构图例 -->
          <div class="hierarchy-legend">
            <div class="legend-item">
              <span class="legend-dot" style="background: #409eff;"></span>
              <span class="legend-text">工厂 L1</span>
            </div>
            <span class="legend-arrow">→</span>
            <div class="legend-item">
              <span class="legend-dot" style="background: #67c23a;"></span>
              <span class="legend-text">部门 L2</span>
            </div>
            <span class="legend-arrow">→</span>
            <div class="legend-item">
              <span class="legend-dot" style="background: #e6a23c;"></span>
              <span class="legend-text">系统 L3</span>
            </div>
            <span class="legend-arrow">→</span>
            <div class="legend-item">
              <span class="legend-dot" style="background: #909399;"></span>
              <span class="legend-text">设备 L4</span>
            </div>
          </div>

          <!-- 选中节点快捷操作工具栏 -->
          <div v-if="selectedNode" class="node-action-panel">
            <div class="node-action-header">
              <el-icon :size="16" :color="getNodeColor(selectedNode)">
                <OfficeBuilding v-if="selectedNode.level_depth === 1" />
                <Folder v-else-if="selectedNode.level_depth === 2" />
                <Operation v-else-if="selectedNode.level_depth === 3" />
                <Cpu v-else />
              </el-icon>
              <span class="node-action-title">{{ selectedNode.location_name }}</span>
              <el-tag size="small" :type="getNodeTagType(selectedNode)" effect="dark">
                {{ getNodeLabel(selectedNode) }}
              </el-tag>
            </div>
            <div v-if="selectedNode.node_type !== 'EQUIPMENT'" class="node-action-btns">
              <el-button v-if="authStore.isAdmin && selectedNode.level_depth === 1" size="small" type="success" @click="openAddLocation(2, selectedNode)">+ 在此工厂下新建部门</el-button>
              <el-button v-if="authStore.isAdmin && selectedNode.level_depth === 2" size="small" type="warning" @click="openAddLocation(3, selectedNode)">+ 在此部门下新建系统</el-button>
              <el-button v-if="selectedNode.level_depth === 3" size="small" type="primary" @click="openCreateDialogWithLocation(selectedNode.id)">+ 在此系统下录入设备</el-button>
              <el-button v-if="authStore.isAdmin" size="small" type="danger" plain :icon="Delete" @click="handleDeleteLocation(selectedNode)">删除节点</el-button>
            </div>
          </div>

          <!-- 未选中节点时的操作提示 -->
          <div v-else class="node-hint">
            <el-icon :size="14" color="#94a3b8"><InfoFilled /></el-icon>
            <span>点击树节点选中，或点击节点右侧按钮快速新增</span>
          </div>

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
                <span class="tree-node-left">
                  <el-icon :size="14" :color="getNodeColor(data)">
                    <OfficeBuilding v-if="data.level_depth === 1" />
                    <Folder v-else-if="data.level_depth === 2" />
                    <Operation v-else-if="data.level_depth === 3" />
                    <Cpu v-else />
                  </el-icon>
                  <span class="node-title" :title="data.location_name">{{ data.location_name }}</span>
                  <el-tag size="small" :type="getNodeTagType(data)" effect="plain" class="level-tag">
                    {{ getNodeLabel(data) }}
                  </el-tag>
                </span>
                <span v-if="data.node_type !== 'EQUIPMENT'" class="tree-node-actions" @click.stop>
                  <el-button v-if="authStore.isAdmin && data.level_depth === 1" size="small" type="success" link @click.stop="openAddLocation(2, data)">+部门</el-button>
                  <el-button v-if="authStore.isAdmin && data.level_depth === 2" size="small" type="warning" link @click.stop="openAddLocation(3, data)">+系统</el-button>
                  <el-button v-if="data.level_depth === 3" size="small" type="primary" link @click.stop="openCreateDialogWithLocation(data.id)">+设备</el-button>
                </span>
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <!-- 右侧设备信息与多维检索 -->
      <el-col :xs="24" :md="17">
        <el-card shadow="never" class="equipment-card">
          <!-- 面包屑导航：展示当前选中节点的完整层级路径 -->
          <div class="breadcrumb-bar">
            <el-breadcrumb separator=">">
              <el-breadcrumb-item :to="{ path: '/dashboard' }">
                <el-icon :size="14"><HomeFilled /></el-icon>
                <span style="margin-left: 4px;">设备信息</span>
              </el-breadcrumb-item>
              <el-breadcrumb-item
                v-for="(crumb, idx) in breadcrumbPath"
                :key="idx"
              >
                <span :style="{ color: getNodeColor({ level_depth: crumb.level_depth }) }">
                  {{ crumb.location_name }}
                </span>
              </el-breadcrumb-item>
            </el-breadcrumb>
            <el-tag v-if="selectedNode" size="small" :type="getNodeTagType(selectedNode)" effect="plain">
              {{ getNodeLabel(selectedNode) }}
            </el-tag>
          </div>

          <!-- 选中节点概览统计 -->
          <div v-if="selectedNode && selectedNode.node_type !== 'EQUIPMENT'" class="node-summary">
            <div class="summary-item">
              <span class="summary-label">节点编码</span>
              <span class="summary-value">{{ selectedNode.location_code }}</span>
            </div>
            <el-divider direction="vertical" />
            <div class="summary-item">
              <span class="summary-label">子节点数</span>
              <span class="summary-value">{{ selectedNode.children?.length || 0 }}</span>
            </div>
            <el-divider direction="vertical" />
            <div class="summary-item">
              <span class="summary-label">当前筛选设备</span>
              <span class="summary-value">{{ equipments.length }} 台</span>
            </div>
          </div>

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
              <el-button v-if="filters.locationId" size="small" link @click="clearLocationFilter">清除位置筛选</el-button>
            </div>

            <div class="action-buttons">
              <el-button v-permission="['ADMIN', 'ENGINEER']" type="primary" :icon="Plus" @click="openCreateDialog">录入设备信息</el-button>
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
            <el-table-column prop="equipment_code" label="设备编码" width="130" font-weight="600" />
            <el-table-column prop="equipment_name" label="设备名称" min-width="140" />
            <el-table-column label="所属位置" min-width="160">
              <template #default="{ row }">
                <span class="location-path-cell">{{ getLocationPath(row.location_id) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="model_spec" label="型号规格" width="130" />
            <el-table-column prop="status" label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="getStatusTag(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="累计运行工时" width="140">
              <template #default="{ row }">
                <div class="op-hours-cell">
                  <span style="font-weight: 600;">{{ row.current_operating_hours || 0 }}h</span>
                  <el-tag
                    size="small"
                    :type="row.current_operating_hours >= (row.maintenance_interval_hours || row.maintenance_interval_days * 24) ? 'danger' : ((row.maintenance_interval_hours || row.maintenance_interval_days * 24) - (row.current_operating_hours || 0) <= 48 ? 'warning' : 'success')"
                    style="margin-left: 6px;"
                  >
                    {{ Math.round(((row.current_operating_hours || 0) / (row.maintenance_interval_hours || (row.maintenance_interval_days * 24) || 720)) * 100) }}%
                  </el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="rated_voltage" label="额定电压" width="100" />
            <el-table-column label="设备参数信息" min-width="130">
              <template #default="{ row }">
                <el-button
                  v-if="row.params_text || row.params"
                  type="primary"
                  link
                  size="small"
                  @click="viewParams(row)"
                >
                  查看参数信息
                </el-button>
                <span v-else style="color: #909399; font-size: 12px;">无参数</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="210" fixed="right">
              <template #default="{ row }">
                <el-button
                  type="success"
                  link
                  size="small"
                  @click="openOperatingHoursDialog(row)"
                >
                  填工时
                </el-button>
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

    <!-- 管理员录入位置节点弹窗 (工厂/部门/系统 - 4级架构) -->
    <el-dialog
      v-model="locDialogVisible"
      :title="locDialogTitle"
      width="540px"
      append-to-body
    >
      <el-form ref="locFormRef" :model="locForm" :rules="locFormRules" label-position="top">
        <el-form-item label="节点层级与类型" required>
          <el-radio-group v-model="locForm.level_depth" @change="handleLevelDepthChange">
            <el-radio-button :value="1">🏭 工厂 (L1)</el-radio-button>
            <el-radio-button :value="2">🏢 部门 (L2)</el-radio-button>
            <el-radio-button :value="3">⚙️ 系统 (L3)</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 若是部门(L2)，选择所属工厂 -->
        <el-form-item v-if="locForm.level_depth === 2" label="所属上级工厂 (必选)" prop="parent_id">
          <el-select v-model="locForm.parent_id" placeholder="请选择所属工厂" style="width: 100%;">
            <el-option
              v-for="fac in factoryLocations"
              :key="fac.id"
              :label="`${fac.location_name} (${fac.location_code})`"
              :value="fac.id"
            />
          </el-select>
        </el-form-item>

        <!-- 若是系统(L3)，选择所属部门 -->
        <el-form-item v-if="locForm.level_depth === 3" label="所属上级部门 (必选)" prop="parent_id">
          <el-select v-model="locForm.parent_id" placeholder="请选择所属部门" style="width: 100%;">
            <el-option
              v-for="dep in departmentLocations"
              :key="dep.id"
              :label="dep.full_name"
              :value="dep.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="节点名称" prop="location_name">
          <el-input v-model="locForm.location_name" :placeholder="locNamePlaceholder" />
        </el-form-item>
        <el-form-item label="节点编码" prop="location_code">
          <el-input v-model="locForm.location_code" :placeholder="locCodePlaceholder" />
        </el-form-item>
        <el-form-item label="排序权重">
          <el-input-number v-model="locForm.sort_order" :min="0" :max="999" style="width: 100%;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="locDialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="savingLoc" @click="submitAddLocation">保 存</el-button>
      </template>
    </el-dialog>

    <!-- 录入设备信息弹窗 (第4级设备挂载与设备参数信息自由录入) -->
    <el-dialog
      v-model="createDialogVisible"
      title="录入新设备信息"
      width="640px"
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
            <el-form-item label="型号规格" prop="model_spec">
              <el-input v-model="form.model_spec" placeholder="如: Y4-73 No.8D" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属系统节点 (第3级系统)" prop="location_id">
              <el-select
                v-model="form.location_id"
                placeholder="请选择所属系统节点"
                filterable
                style="width: 100%;"
              >
                <el-option
                  v-for="sys in systemLocations"
                  :key="sys.id"
                  :label="sys.full_path"
                  :value="sys.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="额定电压">
              <el-input v-model="form.rated_voltage" placeholder="如: 380V" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 设备参数信息 (用户自由文本录入) -->
        <el-form-item label="设备参数信息 (支持自定义自由文本填写设备专有参数、技术指标)">
          <el-input
            v-model="form.params_text"
            type="textarea"
            :rows="6"
            placeholder="请在此输入设备专有技术参数，支持任意格式，如：
额定风量: 12000 m³/h
全压: 1800 Pa
主轴转速: 1450 rpm
通信协议: Modbus TCP
IP地址: 192.168.1.50
绝缘等级: F级
防护等级: IP55"
          />
        </el-form-item>
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

    <!-- 设备参数信息展示弹窗 -->
    <el-dialog v-model="paramDialogVisible" title="设备参数信息明细" width="520px">
      <div v-if="currentParamsText" class="params-display-box">
        <pre class="params-text-content">{{ currentParamsText }}</pre>
      </div>
      <el-descriptions v-else-if="Object.keys(currentParams).length > 0" border :column="1">
        <el-descriptions-item
          v-for="(val, key) in currentParams"
          :key="key"
          :label="String(key)"
        >
          {{ val }}
        </el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="暂无参数信息" />
    </el-dialog>

    <!-- 设备运行工时填报弹窗 (SWR-MNT-012) -->
    <el-dialog
      v-model="opHoursDialogVisible"
      :title="`机台 [${currentOpHoursRow?.equipment_code}] 运行工时填报`"
      width="500px"
      append-to-body
    >
      <div v-if="currentOpHoursRow" class="op-dialog-summary">
        <div><strong>设备名称：</strong>{{ currentOpHoursRow.equipment_name }}</div>
        <div style="margin-top: 6px;">
          <strong>当前累计工时：</strong>
          <span style="color: #409eff; font-weight: 700;">{{ currentOpHoursRow.current_operating_hours || 0 }}</span> / {{ currentOpHoursRow.maintenance_interval_hours || (currentOpHoursRow.maintenance_interval_days * 24) }} 小时
        </div>
      </div>

      <el-form label-position="top" style="margin-top: 14px;">
        <el-form-item label="工时发生日期" required>
          <el-date-picker
            v-model="opHoursForm.log_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%;"
          />
        </el-form-item>
        <el-form-item label="当日开机运行工时 (小时)" required>
          <el-input-number
            v-model="opHoursForm.duration_hours"
            :min="0.5"
            :max="24.0"
            :step="0.5"
            :precision="1"
            style="width: 100%;"
          />
        </el-form-item>
        <el-form-item label="生产说明 / 备注">
          <el-input
            v-model="opHoursForm.remarks"
            type="textarea"
            :rows="2"
            placeholder="如: 白班运转、间歇性试机等..."
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="opHoursDialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="submittingOpHours" @click="submitEquipmentOperatingHours">
          确认录入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import apiClient from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import { ElMessage, ElMessageBox, FormInstance } from 'element-plus';
import {
  OfficeBuilding,
  Folder,
  Operation,
  Cpu,
  Refresh,
  Search,
  Plus,
  Download,
  Delete,
  HomeFilled,
  InfoFilled,
  ArrowDown,
} from '@element-plus/icons-vue';

const authStore = useAuthStore();

const loading = ref(false);
const equipments = ref<any[]>([]);
const locationTree = ref<any[]>([]);
const selectedNode = ref<any>(null);
const treeProps = { children: 'children', label: 'location_name' };

// 所有工厂节点 (Level 1)
const factoryLocations = computed(() => {
  return locationTree.value.filter((n: any) => n.level_depth === 1 && n.node_type !== 'EQUIPMENT');
});

// 所有部门节点 (Level 2)
const departmentLocations = computed(() => {
  const result: any[] = [];
  for (const fac of locationTree.value) {
    if (fac.level_depth === 1 && fac.children) {
      for (const dep of fac.children) {
        if (dep.level_depth === 2 && dep.node_type !== 'EQUIPMENT') {
          result.push({
            id: dep.id,
            location_name: dep.location_name,
            location_code: dep.location_code,
            full_name: `${fac.location_name} > ${dep.location_name}`,
            parent_id: fac.id,
          });
        }
      }
    }
  }
  return result;
});

// 所有系统节点 (Level 3 - 用于挂载设备)
const systemLocations = computed(() => {
  const result: any[] = [];
  for (const fac of locationTree.value) {
    if (fac.children) {
      for (const dep of fac.children) {
        if (dep.children) {
          for (const sys of dep.children) {
            if (sys.level_depth === 3 && sys.node_type !== 'EQUIPMENT') {
              result.push({
                id: sys.id,
                location_name: sys.location_name,
                location_code: sys.location_code,
                full_path: `${fac.location_name} > ${dep.location_name} > ${sys.location_name}`,
                parent_id: dep.id,
              });
            }
          }
        }
      }
    }
  }
  return result;
});

// 扁平化节点映射表：id -> node，用于面包屑路径解析和位置路径展示
const locationMap = ref<Record<string, any>>({});

// 面包屑路径：根据 selectedNode 的 tree_path 解析出完整路径
const breadcrumbPath = computed(() => {
  if (!selectedNode.value) return [];
  const treePath = selectedNode.value.tree_path || '';
  const ids = treePath.split('/').filter(Boolean);
  return ids.map((id: string) => locationMap.value[id]).filter(Boolean);
});

// 获取设备的完整所属位置路径（工厂 > 部门 > 系统）
const getLocationPath = (locId: number): string => {
  const node = locationMap.value[String(locId)];
  if (!node || !node.tree_path) return '-';
  const ids = node.tree_path.split('/').filter(Boolean);
  const names = ids.map((id: string) => locationMap.value[id]?.location_name).filter(Boolean);
  return names.join(' > ') || node.location_name || '-';
};

// 将树形数据递归扁平化为 id -> node 的映射
const buildLocationMap = (nodes: any[]) => {
  const map: Record<string, any> = {};
  const walk = (list: any[]) => {
    for (const n of list) {
      map[String(n.id)] = n;
      if (n.children && n.children.length > 0) {
        walk(n.children);
      }
    }
  };
  walk(nodes);
  locationMap.value = map;
};

const filters = reactive({
  keyword: '',
  equipmentType: '',
  status: '',
  locationId: null as number | null,
});

// 管理员录入位置节点 (工厂/部门/系统)
const locDialogVisible = ref(false);
const savingLoc = ref(false);
const locFormRef = ref<FormInstance>();
const locForm = reactive({
  parent_id: null as number | null,
  level_depth: 1,
  node_type: 'FACTORY',
  location_name: '',
  location_code: '',
  sort_order: 1,
});

const locDialogTitle = computed(() => {
  if (locForm.level_depth === 1) return '管理员录入: 新增工厂节点 (Level 1)';
  if (locForm.level_depth === 2) return '管理员录入: 新增部门节点 (Level 2)';
  return '管理员录入: 新增系统节点 (Level 3)';
});

const locNamePlaceholder = computed(() => {
  if (locForm.level_depth === 1) return '如: 总装制造二厂';
  if (locForm.level_depth === 2) return '如: 动力循环运维部';
  return '如: 主排风动力循环系统';
});

const locCodePlaceholder = computed(() => {
  if (locForm.level_depth === 1) return '如: LOC-FAC-02';
  if (locForm.level_depth === 2) return '如: LOC-DEP-02';
  return '如: LOC-SYS-02';
});

const locFormRules = computed(() => ({
  location_name: [{ required: true, message: '请输入节点名称', trigger: 'blur' }],
  location_code: [{ required: true, message: '请输入节点编码', trigger: 'blur' }],
  parent_id: locForm.level_depth > 1 ? [{ required: true, message: locForm.level_depth === 2 ? '请选择所属上级工厂' : '请选择所属上级部门', trigger: 'change' }] : [],
}));

const openAddLocation = (level: number = 1, parent?: any) => {
  locForm.level_depth = level;
  locForm.node_type = level === 1 ? 'FACTORY' : level === 2 ? 'DEPARTMENT' : 'SYSTEM';
  locForm.location_name = '';
  locForm.location_code = '';
  locForm.sort_order = 1;

  if (parent) {
    locForm.parent_id = parent.id;
  } else if (level === 2) {
    if (selectedNode.value?.level_depth === 1 && selectedNode.value.node_type !== 'EQUIPMENT') {
      locForm.parent_id = selectedNode.value.id;
    } else {
      locForm.parent_id = factoryLocations.value[0]?.id || null;
    }
  } else if (level === 3) {
    if (selectedNode.value?.level_depth === 2 && selectedNode.value.node_type !== 'EQUIPMENT') {
      locForm.parent_id = selectedNode.value.id;
    } else {
      locForm.parent_id = departmentLocations.value[0]?.id || null;
    }
  } else {
    locForm.parent_id = null;
  }

  locFormRef.value?.clearValidate();
  locDialogVisible.value = true;
};

const handleLevelDepthChange = (newLevel: number) => {
  locForm.level_depth = newLevel;
  locForm.node_type = newLevel === 1 ? 'FACTORY' : newLevel === 2 ? 'DEPARTMENT' : 'SYSTEM';
  if (newLevel === 1) {
    locForm.parent_id = null;
  } else if (newLevel === 2) {
    locForm.parent_id = factoryLocations.value[0]?.id || null;
  } else if (newLevel === 3) {
    locForm.parent_id = departmentLocations.value[0]?.id || null;
  }
  locFormRef.value?.clearValidate();
};

const submitAddLocation = async () => {
  if (!locFormRef.value) return;
  await locFormRef.value.validate(async (valid) => {
    if (!valid) return;
    savingLoc.value = true;
    try {
      const res = await apiClient.post<any, any>('/locations', {
        parent_id: locForm.parent_id,
        location_name: locForm.location_name,
        location_code: locForm.location_code,
        node_type: locForm.node_type,
        sort_order: locForm.sort_order,
      });
      if (res.code === 200) {
        ElMessage.success('位置层级节点创建成功');
        locDialogVisible.value = false;
        fetchLocationTree();
      }
    } catch (err) {
      console.error(err);
    } finally {
      savingLoc.value = false;
    }
  });
};

const handleDeleteLocation = async (node: any) => {
  try {
    await ElMessageBox.confirm(`确认删除拓扑节点【${node.location_name}】？`, '警告', { type: 'warning' });
    const res = await apiClient.delete<any, any>(`/locations/${node.id}`);
    if (res.code === 200) {
      ElMessage.success('拓扑节点删除成功');
      selectedNode.value = null;
      fetchLocationTree();
    }
  } catch (err) {
    // cancelled
  }
};

const openCreateDialogWithLocation = (locId: number) => {
  form.equipment_code = '';
  form.equipment_name = '';
  form.model_spec = '';
  form.location_id = locId;
  form.rated_voltage = '380V';
  form.params_text = '';
  formRef.value?.resetFields();
  createDialogVisible.value = true;
};

const createDialogVisible = ref(false);
const saving = ref(false);
const formRef = ref<FormInstance>();
const form = reactive({
  equipment_code: '',
  equipment_name: '',
  model_spec: '',
  location_id: null as number | null,
  rated_voltage: '380V',
  params_text: '',
});

const formRules = {
  equipment_code: [{ required: true, message: '请输入设备编码', trigger: 'blur' }],
  equipment_name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  location_id: [{ required: true, message: '请选择所属系统节点', trigger: 'change' }],
};

// 电子履历
const timelineVisible = ref(false);
const timelineLoading = ref(false);
const currentEquipment = ref<any>(null);
const timelineList = ref<any[]>([]);

// 参数展示
const paramDialogVisible = ref(false);
const currentParams = ref<Record<string, any>>({});
const currentParamsText = ref<string>('');

const getNodeColor = (node: any) => {
  if (node.level_depth === 1) return '#409eff';
  if (node.level_depth === 2) return '#67c23a';
  if (node.level_depth === 3) return '#e6a23c';
  return '#909399';
};

const getNodeTagType = (node: any) => {
  if (node.level_depth === 1) return 'primary';
  if (node.level_depth === 2) return 'success';
  if (node.level_depth === 3) return 'warning';
  return 'info';
};

const getNodeLabel = (node: any) => {
  if (node.level_depth === 1) return '工厂 L1';
  if (node.level_depth === 2) return '部门 L2';
  if (node.level_depth === 3) return '系统 L3';
  return '设备 L4';
};

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
    const res = await apiClient.get<any, any>('/locations/tree?include_equipments=true');
    if (res.code === 200) {
      locationTree.value = res.data;
      buildLocationMap(res.data);
    }
  } catch (err) {
    console.error(err);
  }
};

const handleNodeClick = (node: any) => {
  if (!node) return;
  // node_type 兜底：若后端未返回或为默认值 "SYSTEM"，根据 level_depth 推断
  if (!node.node_type || node.node_type === 'SYSTEM') {
    if (node.level_depth === 1) node.node_type = 'FACTORY';
    else if (node.level_depth === 2) node.node_type = 'DEPARTMENT';
    else if (node.level_depth === 3) node.node_type = 'SYSTEM';
    else if (node.level_depth === 4) node.node_type = 'EQUIPMENT';
  }
  selectedNode.value = node;
  if (node.node_type === 'EQUIPMENT' && node.equipment_id) {
    filters.keyword = node.location_code;
    fetchEquipments();
  } else {
    filters.locationId = typeof node.id === 'number' ? node.id : null;
    fetchEquipments();
  }
};

const clearLocationFilter = () => {
  filters.locationId = null;
  filters.keyword = '';
  selectedNode.value = null;
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
      let items = res.data.items;
      if (filters.keyword) {
        const kw = filters.keyword.toLowerCase();
        items = items.filter((i: any) =>
          i.equipment_name.toLowerCase().includes(kw) ||
          i.equipment_code.toLowerCase().includes(kw)
        );
      }
      if (filters.locationId) {
        items = items.filter((i: any) => i.location_id === filters.locationId);
      }
      equipments.value = items;
    }
  } catch (err) {
    console.error(err);
  } finally {
    loading.value = false;
  }
};

const openCreateDialog = () => {
  // 重置表单
  form.equipment_code = '';
  form.equipment_name = '';
  form.model_spec = '';
  if (selectedNode.value?.level_depth === 3 && selectedNode.value.node_type !== 'EQUIPMENT') {
    form.location_id = selectedNode.value.id;
  } else {
    form.location_id = systemLocations.value[0]?.id || null;
  }
  form.rated_voltage = '380V';
  form.params_text = '';
  formRef.value?.resetFields();
  createDialogVisible.value = true;
};

const submitCreate = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    saving.value = true;
    try {
      const payload: any = {
        equipment_code: form.equipment_code,
        equipment_name: form.equipment_name,
        model_spec: form.model_spec,
        location_id: form.location_id,
        rated_voltage: form.rated_voltage,
        params_text: form.params_text,
        equipment_type: 'GENERAL',
        work_type: 'GENERAL',
      };
      const res = await apiClient.post<any, any>('/equipments', payload);
      if (res.code === 200) {
        ElMessage.success('设备信息录入成功');
        createDialogVisible.value = false;
        fetchEquipments();
        fetchLocationTree();
      }
    } catch (err) {
      console.error(err);
    } finally {
      saving.value = false;
    }
  });
};

const viewParams = (row: any) => {
  currentParamsText.value = row.params_text || '';
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

const opHoursDialogVisible = ref(false);
const submittingOpHours = ref(false);
const currentOpHoursRow = ref<any>(null);
const opHoursForm = reactive({
  log_date: new Date().toISOString().split('T')[0],
  duration_hours: 8.0,
  remarks: '',
});

const openOperatingHoursDialog = (row: any) => {
  currentOpHoursRow.value = row;
  opHoursForm.log_date = new Date().toISOString().split('T')[0];
  opHoursForm.duration_hours = 8.0;
  opHoursForm.remarks = '';
  opHoursDialogVisible.value = true;
};

const submitEquipmentOperatingHours = async () => {
  if (!currentOpHoursRow.value) return;
  if (!opHoursForm.duration_hours || opHoursForm.duration_hours <= 0 || opHoursForm.duration_hours > 24) {
    ElMessage.warning('当日运行工时需在 0.1 至 24.0 小时之间');
    return;
  }
  submittingOpHours.value = true;
  try {
    const payload = {
      equipment_id: currentOpHoursRow.value.id,
      log_date: opHoursForm.log_date,
      duration_hours: opHoursForm.duration_hours,
      remarks: opHoursForm.remarks,
    };
    const res = await apiClient.post<any, any>(
      `/equipments/${currentOpHoursRow.value.id}/operating-hours`,
      payload
    );
    if (res.code === 200) {
      if (res.data?.triggered_maintenance) {
        await ElMessageBox.alert(
          `工时记录成功！机台累计运行工时达到 ${res.data.current_operating_hours}h，已达到预警/维护阈值并触发维保工单派发及邮件通知！`,
          '维保工时预警提示',
          { type: 'warning' }
        );
      } else {
        ElMessage.success(`工时录入成功，当前累计运行工时: ${res.data.current_operating_hours} 小时`);
      }
      opHoursDialogVisible.value = false;
      fetchEquipments();
    }
  } catch (err) {
    console.error(err);
  } finally {
    submittingOpHours.value = false;
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

.header-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-weight: 600;
  font-size: 15px;
  color: #1e293b;
}

/* 层级结构图例 */
.hierarchy-legend {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.legend-text {
  font-size: 11px;
  color: #475569;
  font-weight: 500;
}

.legend-arrow {
  color: #94a3b8;
  font-size: 11px;
}

/* 节点操作面板 */
.node-action-panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.node-action-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.node-action-title {
  font-weight: 600;
  font-size: 14px;
  color: #0f172a;
  flex: 1;
}

.node-action-btns {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  flex-wrap: wrap;
}

/* 未选中节点提示 */
.node-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  margin-bottom: 12px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  font-size: 12px;
  color: #94a3b8;
}

/* 快速新增栏 */
.quick-add-bar {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.quick-add-bar .el-button {
  margin: 0;
  flex: 1;
  font-size: 11px;
  padding: 5px 6px;
}

/* 树节点 */
.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 6px;
  font-size: 13px;
  padding: 2px 0;
}

.tree-node-left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  overflow: hidden;
}

.tree-node-actions {
  display: none;
}

.tree-node:hover .tree-node-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.tree-node-actions .el-button {
  padding: 2px 4px;
  font-size: 11px;
  height: auto;
}

.node-title {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.level-tag {
  font-size: 10px;
  margin-left: 4px;
  padding: 0 4px;
}

/* 右侧面板 */
.equipment-card {
  min-height: calc(100vh - 120px);
}

/* 面包屑导航 */
.breadcrumb-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  margin-bottom: 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

/* 节点概览统计 */
.node-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  margin-bottom: 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  flex-wrap: wrap;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.summary-label {
  font-size: 12px;
  color: #64748b;
}

.summary-value {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

/* 位置路径列 */
.location-path-cell {
  font-size: 12px;
  color: #475569;
  line-height: 1.4;
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

.op-hours-cell {
  display: flex;
  align-items: center;
}

.op-dialog-summary {
  background: #f8fafc;
  padding: 12px 14px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  font-size: 14px;
}

.params-display-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 14px;
  max-height: 400px;
  overflow-y: auto;
}

.params-text-content {
  margin: 0;
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace, sans-serif;
  font-size: 13px;
  line-height: 1.6;
  color: #1e293b;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>