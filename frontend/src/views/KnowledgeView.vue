<template>
  <div class="knowledge-view">
    <div class="page-header">
      <div class="header-titles">
        <h2>排查排故知识库与经验资产</h2>
        <p>基于闭环工单自动沉淀、多维 Facet 检索及典型案例库 (SWR-KB-002/003/005/006)</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Download" @click="exportExcel">导出知识手册</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">录入知识条目</el-button>
      </div>
    </div>

    <!-- 搜索与多维 Facet 过滤卡片 (SWR-KB-003) -->
    <el-card shadow="never" class="filter-card">
      <div class="search-row">
        <el-input
          v-model="searchKeyword"
          placeholder="输入故障现象、设备型号、根因关键词全文模糊检索..."
          size="large"
          clearable
          :prefix-icon="Search"
          class="search-input"
          @keyup.enter="handleSearch"
        />
        <el-button type="primary" size="large" @click="handleSearch">全 文 检 索</el-button>
      </div>

      <div class="facet-row">
        <span class="facet-label">多维分类筛选：</span>
        <el-radio-group v-model="selectedType" size="small" @change="handleSearch">
          <el-radio-button label="">全部设备</el-radio-button>
          <el-radio-button label="FAN">工业风机</el-radio-button>
          <el-radio-button label="MOTOR">三相电机</el-radio-button>
          <el-radio-button label="PLC">PLC控制器</el-radio-button>
          <el-radio-button label="SENSOR">传感器</el-radio-button>
        </el-radio-group>

        <el-checkbox v-model="onlyFeatured" label="只看标定典型案例★" @change="handleSearch" style="margin-left: 20px;" />
      </div>
    </el-card>

    <!-- 知识条目卡片瀑布流列表 -->
    <div class="articles-container" v-loading="loading">
      <el-empty v-if="articles.length === 0" description="未检索到匹配的知识库条目" />

      <div v-else class="article-grid">
        <el-card
          v-for="item in articles"
          :key="item.id"
          shadow="hover"
          class="article-card"
          :class="{ 'is-featured': item.is_featured }"
          @click="openDetail(item)"
        >
          <div class="card-head">
            <div class="badges">
              <el-tag size="small" type="primary">{{ item.equipment_type }}</el-tag>
              <el-tag size="small" type="info">{{ item.fault_system }}</el-tag>
              <el-tag v-if="item.is_featured" size="small" type="warning" effect="dark">典型推荐★</el-tag>
            </div>
            <span class="view-count">{{ item.view_count || 0 }} 次查阅</span>
          </div>

          <h3 class="article-title">{{ item.fault_title }}</h3>

          <div class="article-body">
            <div class="section-row">
              <span class="tag-title">现象特征:</span>
              <p class="section-desc">{{ item.fault_phenomenon }}</p>
            </div>
            <div class="section-row">
              <span class="tag-title">根本原因:</span>
              <p class="section-desc root-cause">{{ item.root_cause }}</p>
            </div>
          </div>

          <div class="card-tags">
            <el-tag
              v-for="(tag, tidx) in item.tags"
              :key="tidx"
              size="small"
              type="info"
              effect="plain"
            >
              {{ tag }}
            </el-tag>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 知识条目详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="`排故方案详情 - ${currentArticle?.fault_title}`"
      width="680px"
      append-to-body
    >
      <div v-if="currentArticle" class="detail-content">
        <div class="detail-header-meta">
          <el-tag>{{ currentArticle.equipment_type }} ({{ currentArticle.equipment_model }})</el-tag>
          <el-tag type="info">归属系统: {{ currentArticle.fault_system }}</el-tag>
          <el-tag v-if="currentArticle.is_featured" type="warning">典型示范案例</el-tag>
        </div>

        <div class="detail-section">
          <h4>故障现象与表征</h4>
          <p class="content-box">{{ currentArticle.fault_phenomenon }}</p>
        </div>

        <div class="detail-section">
          <h4>根本原因分析 (Root Cause)</h4>
          <p class="content-box cause-box">{{ currentArticle.root_cause }}</p>
        </div>

        <div class="detail-section">
          <h4>标准化解决与排查步骤 (SOP)</h4>
          <pre class="content-box solution-box">{{ currentArticle.solution_steps }}</pre>
        </div>
      </div>
    </el-dialog>

    <!-- 人工录入与精编弹窗 (SWR-KB-005) -->
    <el-dialog
      v-model="createVisible"
      title="录入与精编知识条目"
      width="600px"
      append-to-body
    >
      <el-form ref="formRef" :model="formData" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="设备类型" required>
              <el-select v-model="formData.equipment_type" style="width: 100%;">
                <el-option label="工业风机" value="FAN" />
                <el-option label="三相电机" value="MOTOR" />
                <el-option label="PLC控制器" value="PLC" />
                <el-option label="通用设备" value="OTHER" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="适用型号" required>
              <el-input v-model="formData.equipment_model" placeholder="如: Y4-73" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="归属系统 (如: 供电系统/润滑系统)" required>
          <el-input v-model="formData.fault_system" />
        </el-form-item>

        <el-form-item label="故障标题" required>
          <el-input v-model="formData.fault_title" placeholder="简要概括" />
        </el-form-item>

        <el-form-item label="故障现象描述" required>
          <el-input v-model="formData.fault_phenomenon" type="textarea" :rows="2" />
        </el-form-item>

        <el-form-item label="根本原因" required>
          <el-input v-model="formData.root_cause" type="textarea" :rows="2" />
        </el-form-item>

        <el-form-item label="标准解决排查步骤" required>
          <el-input v-model="formData.solution_steps" type="textarea" :rows="3" />
        </el-form-item>

        <el-form-item label="是否标定为典型案例 (SWR-KB-005)">
          <el-switch v-model="formData.is_featured" active-text="典型案例" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import apiClient from '@/api/client';
import { ElMessage } from 'element-plus';
import { Search, Plus, Download } from '@element-plus/icons-vue';

const loading = ref(false);
const articles = ref<any[]>([]);
const searchKeyword = ref('');
const selectedType = ref('');
const onlyFeatured = ref(false);

const detailVisible = ref(false);
const currentArticle = ref<any>(null);

const createVisible = ref(false);
const saving = ref(false);
const formData = reactive({
  equipment_type: 'FAN',
  equipment_model: 'Y4-73',
  fault_system: '传动系统',
  fault_title: '',
  fault_phenomenon: '',
  root_cause: '',
  solution_steps: '',
  is_featured: true,
  tags: ['#风机', '#异响'],
});

const handleSearch = async () => {
  loading.value = true;
  try {
    let url = `/knowledge/search?limit=50`;
    if (searchKeyword.value) url += `&keyword=${encodeURIComponent(searchKeyword.value)}`;
    if (selectedType.value) url += `&equipment_type=${selectedType.value}`;
    if (onlyFeatured.value) url += `&is_featured=true`;

    const res = await apiClient.get<any, any>(url);
    if (res.code === 200 && res.data?.items) {
      articles.value = res.data.items;
    }
  } catch (err) {
    console.error(err);
  } finally {
    loading.value = false;
  }
};

const openDetail = (item: any) => {
  currentArticle.value = item;
  detailVisible.value = true;
};

const openCreateDialog = () => {
  createVisible.value = true;
};

const submitCreate = async () => {
  if (!formData.fault_title || !formData.root_cause || !formData.solution_steps) {
    ElMessage.warning('请补全必填信息');
    return;
  }
  saving.value = true;
  try {
    const res = await apiClient.post<any, any>('/knowledge', formData);
    if (res.code === 200) {
      ElMessage.success('知识条目已收录并生成向量索引');
      createVisible.value = false;
      handleSearch();
    }
  } catch (err) {
    console.error(err);
  } finally {
    saving.value = false;
  }
};

const exportExcel = () => {
  window.open('/api/v1/knowledge/export/excel', '_blank');
};

onMounted(() => {
  handleSearch();
});
</script>

<style scoped>
.knowledge-view {
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

.filter-card {
  border-radius: 8px;
}

.search-row {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
}

.search-input {
  flex: 1;
}

.facet-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.facet-label {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
}

.article-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

@media (max-width: 1024px) {
  .article-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .article-grid {
    grid-template-columns: 1fr;
  }
}

.article-card {
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
}

.article-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
}

.article-card.is-featured {
  border-top: 3px solid #f59e0b;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.badges {
  display: flex;
  gap: 6px;
}

.view-count {
  font-size: 12px;
  color: #94a3b8;
}

.article-title {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #1e293b;
  font-weight: 600;
}

.article-body {
  font-size: 13px;
  color: #475569;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.tag-title {
  font-weight: 600;
  color: #64748b;
  font-size: 12px;
}

.section-desc {
  margin: 2px 0 0 0;
  line-height: 1.4;
}

.root-cause {
  color: #dc2626;
}

.card-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: auto;
}

.detail-header-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section h4 {
  margin: 0 0 6px 0;
  font-size: 14px;
  color: #1e293b;
}

.content-box {
  background-color: #f8fafc;
  padding: 12px;
  border-radius: 6px;
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #334155;
}

.cause-box {
  background-color: #fef2f2;
  color: #991b1b;
}

.solution-box {
  white-space: pre-wrap;
  font-family: inherit;
  background-color: #f0fdf4;
  color: #166534;
}
</style>
