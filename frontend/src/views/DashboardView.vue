<template>
  <div class="dashboard-view">
    <!-- 顶部欢迎与统计概览 -->
    <div class="page-title-section">
      <div class="title-text">
        <h2>FCM设备运维管理平台</h2>
        <p>实时监控车间设备运行状态、SLA 履约指标及个性化待办工单 (SWR-DSH-001/002/003)</p>
      </div>
      <el-button type="primary" :icon="Refresh" @click="fetchDashboardData">刷新实时数据</el-button>
    </div>

    <!-- 指标卡片 (SWR-DSH-001) -->
    <el-row :gutter="16" class="metric-cards">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="metric-card card-total">
          <div class="metric-header">
            <span class="metric-label">在册设备总数</span>
            <el-icon :size="24" color="#409eff"><Cpu /></el-icon>
          </div>
          <div class="metric-value">{{ metrics.total_equipments || 0 }} <span class="unit">台</span></div>
          <div class="metric-sub">运行率: {{ runningRate }}%</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="metric-card card-running">
          <div class="metric-header">
            <span class="metric-label">正常运行中</span>
            <el-icon :size="24" color="#67c23a"><CircleCheckFilled /></el-icon>
          </div>
          <div class="metric-value text-success">{{ metrics.running_count || 0 }} <span class="unit">台</span></div>
          <div class="metric-sub">计划停机: {{ metrics.shutdown_count || 0 }} 台</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="metric-card card-faulty">
          <div class="metric-header">
            <span class="metric-label">当前故障报修</span>
            <el-icon :size="24" color="#f56c6c"><WarningFilled /></el-icon>
          </div>
          <div class="metric-value text-danger">{{ metrics.faulty_count || 0 }} <span class="unit">起</span></div>
          <div class="metric-sub">未闭环单: {{ metrics.open_faults_count || 0 }} 单</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="metric-card card-maintenance">
          <div class="metric-header">
            <span class="metric-label">待巡检维护工单</span>
            <el-icon :size="24" color="#e6a23c"><Calendar /></el-icon>
          </div>
          <div class="metric-value text-warning">{{ metrics.todo_maintenance_count || 0 }} <span class="unit">项</span></div>
          <div class="metric-sub">即将超期倒计时中</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域与角色待办 (SWR-DSH-002/003) -->
    <el-row :gutter="16" class="chart-and-todo-section">
      <!-- 左侧：图表分析 -->
      <el-col :xs="24" :lg="16">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">设备状态与维保工单完成趋势</span>
              <el-radio-group v-model="chartTimeRange" size="small">
                <el-radio-button label="7d">近 7 天</el-radio-button>
                <el-radio-button label="30d">近 30 天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div class="charts-container">
            <div ref="pieChartRef" class="echart-box pie-box"></div>
            <div ref="trendChartRef" class="echart-box trend-box"></div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：角色差异化待办推送 (SWR-DSH-002) -->
      <el-col :xs="24" :lg="8">
        <el-card shadow="hover" class="todo-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">我的个性化待办</span>
              <el-tag size="small" type="danger">{{ todos.length }} 件待办</el-tag>
            </div>
          </template>

          <div v-if="todos.length === 0" class="empty-todo">
            <el-empty description="暂无待办事项，设备运行平稳" />
          </div>

          <div v-else class="todo-list">
            <div
              v-for="(item, idx) in todos"
              :key="idx"
              class="todo-item"
              :class="{ 'is-overdue': item.is_overdue }"
              @click="handleTodoClick(item)"
            >
              <div class="todo-item-header">
                <el-tag size="small" :type="item.type === 'INSPECTION' ? 'primary' : 'danger'">
                  {{ item.type === 'INSPECTION' ? '巡检任务' : '故障抢修' }}
                </el-tag>
                <span v-if="item.is_overdue" class="overdue-tag">SLA 超时</span>
                <span class="todo-time">{{ formatTime(item.due_date) }}</span>
              </div>
              <div class="todo-title">{{ item.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import apiClient from '@/api/client';
import * as echarts from 'echarts';
import {
  Refresh,
  Cpu,
  CircleCheckFilled,
  WarningFilled,
  Calendar,
} from '@element-plus/icons-vue';

const router = useRouter();

const metrics = reactive({
  total_equipments: 0,
  running_count: 0,
  pending_maintenance_count: 0,
  faulty_count: 0,
  shutdown_count: 0,
  todo_maintenance_count: 0,
  open_faults_count: 0,
});

const todos = ref<any[]>([]);
const chartTimeRange = ref('30d');

const pieChartRef = ref<HTMLDivElement>();
const trendChartRef = ref<HTMLDivElement>();
let pieChartInstance: echarts.ECharts | null = null;
let trendChartInstance: echarts.ECharts | null = null;

const runningRate = computed(() => {
  if (!metrics.total_equipments) return 0;
  return Math.round((metrics.running_count / metrics.total_equipments) * 100);
});

const formatTime = (timeStr?: string) => {
  if (!timeStr) return '';
  return timeStr.split('T')[0];
};

const handleTodoClick = (item: any) => {
  if (item.type === 'INSPECTION') {
    router.push('/inspection');
  } else {
    router.push('/faults');
  }
};

const initCharts = () => {
  if (pieChartRef.value) {
    pieChartInstance = echarts.init(pieChartRef.value);
    pieChartInstance.setOption({
      title: { text: '设备状态分布', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'item' },
      legend: { bottom: '0%' },
      color: ['#67c23a', '#e6a23c', '#f56c6c', '#909399'],
      series: [
        {
          name: '设备状态',
          type: 'pie',
          radius: ['45%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          data: [
            { value: metrics.running_count || 12, name: '正常运行' },
            { value: metrics.pending_maintenance_count || 3, name: '待维护' },
            { value: metrics.faulty_count || 1, name: '故障异常' },
            { value: metrics.shutdown_count || 0, name: '计划停机' },
          ],
        },
      ],
    });
  }

  if (trendChartRef.value) {
    trendChartInstance = echarts.init(trendChartRef.value);
    trendChartInstance.setOption({
      title: { text: '维保完成率与故障拦截趋势', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { top: '8%', right: '4%' },
      xAxis: {
        type: 'category',
        data: ['第1周', '第2周', '第3周', '第4周'],
      },
      yAxis: [
        { type: 'value', name: '次数', minInterval: 1 },
        { type: 'value', name: '完成率 %', max: 100 },
      ],
      series: [
        {
          name: '故障报修数',
          type: 'bar',
          data: [5, 3, 4, 2],
          itemStyle: { color: '#f56c6c', borderRadius: [4, 4, 0, 0] },
        },
        {
          name: '巡检完成率',
          type: 'line',
          yAxisIndex: 1,
          data: [92, 95, 98, 100],
          itemStyle: { color: '#409eff' },
          smooth: true,
        },
      ],
    });
  }
};

const fetchDashboardData = async () => {
  try {
    const [metricsRes, todoRes] = await Promise.all([
      apiClient.get<any, any>('/dashboard/metrics'),
      apiClient.get<any, any>('/dashboard/my-todo'),
    ]);

    if (metricsRes.code === 200 && metricsRes.data) {
      Object.assign(metrics, metricsRes.data);
    }
    if (todoRes.code === 200 && todoRes.data) {
      todos.value = todoRes.data;
    }

    await nextTick();
    if (pieChartInstance) {
      pieChartInstance.setOption({
        series: [{
          data: [
            { value: metrics.running_count || 0, name: '正常运行' },
            { value: metrics.pending_maintenance_count || 0, name: '待维护' },
            { value: metrics.faulty_count || 0, name: '故障异常' },
            { value: metrics.shutdown_count || 0, name: '计划停机' },
          ],
        }],
      });
    }
  } catch (err) {
    console.error('Failed to load dashboard data:', err);
  }
};

const handleResize = () => {
  pieChartInstance?.resize();
  trendChartInstance?.resize();
};

onMounted(async () => {
  await fetchDashboardData();
  initCharts();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  pieChartInstance?.dispose();
  trendChartInstance?.dispose();
});
</script>

<style scoped>
.dashboard-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-title-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-text h2 {
  margin: 0 0 6px 0;
  font-size: 22px;
  color: #1e293b;
}

.title-text p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.metric-card {
  border-radius: 10px;
  transition: transform 0.2s;
}

.metric-card:hover {
  transform: translateY(-2px);
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #64748b;
  font-size: 14px;
}

.metric-value {
  margin: 12px 0 6px 0;
  font-size: 30px;
  font-weight: 700;
  color: #1e293b;
}

.unit {
  font-size: 14px;
  font-weight: normal;
  color: #94a3b8;
}

.metric-sub {
  font-size: 12px;
  color: #94a3b8;
}

.text-success { color: #16a34a !important; }
.text-danger { color: #dc2626 !important; }
.text-warning { color: #d97706 !important; }

.chart-and-todo-section {
  margin-top: 4px;
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

.charts-container {
  display: flex;
  flex-wrap: wrap;
  min-height: 340px;
}

.echart-box {
  flex: 1;
  min-width: 280px;
  height: 340px;
}

.todo-card {
  min-height: 410px;
}

.todo-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.todo-item {
  padding: 12px 14px;
  background-color: #f8fafc;
  border-left: 4px solid #409eff;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.todo-item:hover {
  background-color: #eff6ff;
  transform: translateX(4px);
}

.todo-item.is-overdue {
  border-left-color: #ef4444;
  background-color: #fef2f2;
}

.todo-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.overdue-tag {
  font-size: 11px;
  background-color: #ef4444;
  color: #ffffff;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.todo-time {
  font-size: 12px;
  color: #94a3b8;
  margin-left: auto;
}

.todo-title {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
