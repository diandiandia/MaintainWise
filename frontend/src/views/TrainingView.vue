<template>
  <div class="training-view">
    <div class="page-header">
      <div class="header-titles">
        <h2>维保技能实训与终身成长档案</h2>
        <p>支持典型真实案例课程挂接、考核考评闭环及复训触发 (SWR-TRN-001/002/004/005)</p>
      </div>
      <div class="header-actions">
        <el-button v-permission="['ADMIN', 'ENGINEER']" type="primary" :icon="Plus" @click="openCreateCourseDialog">编制实操新课程</el-button>
      </div>
    </div>

    <el-card shadow="never" class="main-card">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 课程库 -->
        <el-tab-pane label="实训与案例课程库" name="courses">
          <div class="courses-grid" v-loading="loadingCourses">
            <el-card
              v-for="c in courses"
              :key="c.id"
              shadow="hover"
              class="course-card"
            >
              <div class="course-header">
                <el-tag size="small" :type="getCategoryTag(c.course_category)">{{ c.course_category }}</el-tag>
                <span class="hours-badge">{{ c.planned_hours }} 课时</span>
              </div>
              <h3 class="course-title">{{ c.course_name }}</h3>
              <p class="course-desc">{{ c.description || '暂无描述' }}</p>
              <div class="course-footer">
                <el-tag size="small" type="success" effect="plain">
                  已挂接 {{ c.cases_count || 1 }} 起真实故障案例 (SWR-TRN-002)
                </el-tag>
                <el-button size="small" type="primary" link>查看大纲</el-button>
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- 员工终身技能电子档案卡 (SWR-TRN-005) -->
        <el-tab-pane label="员工技能电子档案卡" name="profile">
          <div class="profile-container" v-loading="loadingProfile">
            <el-row :gutter="24">
              <!-- 左侧档案卡片 -->
              <el-col :xs="24" :md="8">
                <el-card shadow="hover" class="profile-card">
                  <div class="avatar-center">
                    <el-avatar :size="80" style="background-color: #409eff; font-size: 28px;">
                      {{ userProfile?.full_name?.charAt(0) || '技' }}
                    </el-avatar>
                    <h3 class="user-name">{{ userProfile?.full_name || '技术员' }}</h3>
                    <p class="user-role">
                      <el-tag size="small">{{ userProfile?.role_code }}</el-tag>
                      <el-tag size="small" type="info">{{ userProfile?.work_type }}</el-tag>
                    </p>
                  </div>

                  <el-divider />

                  <div class="profile-stats">
                    <div class="stat-item">
                      <span class="stat-num">{{ userProfile?.total_trainings || 3 }}</span>
                      <span class="stat-lbl">参训总次数</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-num text-success">{{ userProfile?.pass_rate || 92 }}%</span>
                      <span class="stat-lbl">考核通过率</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-num" :class="userProfile?.need_retraining ? 'text-danger' : 'text-success'">
                        {{ userProfile?.need_retraining ? '待复训' : '合格' }}
                      </span>
                      <span class="stat-lbl">复训状态</span>
                    </div>
                  </div>
                </el-card>
              </el-col>

              <!-- 右侧考核与培训履历 -->
              <el-col :xs="24" :md="16">
                <el-card shadow="hover" class="history-card">
                  <template #header>
                    <div class="card-header">
                      <span class="header-title">历次实操考核与打分明细</span>
                    </div>
                  </template>

                  <el-table :data="userProfile?.history || defaultHistory" border stripe>
                    <el-table-column prop="date" label="考评日期" width="130" />
                    <el-table-column prop="assessment_type" label="考评类型" width="130" />
                    <el-table-column prop="score" label="综合得分" width="110">
                      <template #default="{ row }">
                        <span :class="row.score >= 80 ? 'text-success' : 'text-danger'" style="font-weight: 700;">
                          {{ row.score }} 分
                        </span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="is_passed" label="评定结果" width="110">
                      <template #default="{ row }">
                        <el-tag :type="row.is_passed ? 'success' : 'danger'">
                          {{ row.is_passed ? '通过' : '不合格' }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="need_retraining" label="是否触发复训">
                      <template #default="{ row }">
                        <span v-if="row.need_retraining" style="color: #ef4444; font-size: 13px;">
                          ⚠️ 触发重新复训 (SWR-TRN-004)
                        </span>
                        <span v-else style="color: #10b981; font-size: 13px;">免复训</span>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 编制课程弹窗 (SWR-TRN-001/002) -->
    <el-dialog
      v-model="createDialogVisible"
      title="编制实操课程并挂接典型故障案例"
      width="600px"
      append-to-body
    >
      <el-form ref="courseFormRef" :model="courseForm" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="课程编码" required>
              <el-input v-model="courseForm.course_code" placeholder="如: TRN-MEC-01" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="课程分类" required>
              <el-select v-model="courseForm.course_category" style="width: 100%;">
                <el-option label="机械维修技能" value="MECHANICAL" />
                <el-option label="电气安全与PLC" value="ELECTRICAL" />
                <el-option label="安全与规范规程" value="SAFETY" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="课程名称" required>
          <el-input v-model="courseForm.course_name" placeholder="如: 离心风机振动超标排查与动平衡校正实训" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="规划实训学时">
              <el-input-number v-model="courseForm.planned_hours" :min="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="挂接知识库真实案例ID (SWR-TRN-002)">
              <el-input-number v-model="courseForm.case_article_id" :min="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="实操训练目标与要点">
          <el-input v-model="courseForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="savingCourse" @click="submitCourse">保存课程并挂接案例</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import apiClient from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import { ElMessage } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';

const authStore = useAuthStore();
const activeTab = ref('courses');

const loadingCourses = ref(false);
const courses = ref<any[]>([]);

const loadingProfile = ref(false);
const userProfile = ref<any>(null);

const createDialogVisible = ref(false);
const savingCourse = ref(false);
const courseForm = reactive({
  course_code: 'TRN-2026-01',
  course_category: 'MECHANICAL',
  course_name: '工业离心风机异响与润滑故障处置实训',
  planned_hours: 4.0,
  case_article_id: 1,
  description: '结合车间真实历史停机故障案例，针对轴承润滑失效及叶轮动平衡偏差进行拆解比对教学',
});

const defaultHistory = [
  { date: '2026-08-10', assessment_type: '现场实操', score: 88, is_passed: true, need_retraining: false },
  { date: '2026-07-15', assessment_type: '理论笔试', score: 94, is_passed: true, need_retraining: false },
  { date: '2026-06-20', assessment_type: '带电规程抽检', score: 58, is_passed: false, need_retraining: true },
];

const getCategoryTag = (cat?: string) => {
  switch (cat) {
    case 'MECHANICAL': return 'primary';
    case 'ELECTRICAL': return 'warning';
    case 'SAFETY': return 'danger';
    default: return 'info';
  }
};

const handleTabChange = (tab: any) => {
  if (tab === 'courses') fetchCourses();
  else if (tab === 'profile') fetchProfile();
};

const fetchCourses = async () => {
  loadingCourses.value = true;
  try {
    const res = await apiClient.get<any, any>('/training/courses');
    if (res.code === 200 && res.data) {
      courses.value = res.data;
    }
  } catch (err) {
    console.error(err);
  } finally {
    loadingCourses.value = false;
  }
};

const fetchProfile = async () => {
  loadingProfile.value = true;
  try {
    const userId = authStore.userInfo?.id || 1;
    const res = await apiClient.get<any, any>(`/training/profile/${userId}`);
    if (res.code === 200 && res.data) {
      userProfile.value = res.data;
    }
  } catch (err) {
    console.error(err);
  } finally {
    loadingProfile.value = false;
  }
};

const openCreateCourseDialog = () => {
  createDialogVisible.value = true;
};

const submitCourse = async () => {
  if (!courseForm.course_name) {
    ElMessage.warning('请输入课程名称');
    return;
  }
  savingCourse.value = true;
  try {
    const res = await apiClient.post<any, any>('/training/courses', {
      course_code: courseForm.course_code,
      course_name: courseForm.course_name,
      course_category: courseForm.course_category,
      planned_hours: courseForm.planned_hours,
      description: courseForm.description,
      case_article_ids: courseForm.case_article_id ? [courseForm.case_article_id] : [],
    });
    if (res.code === 200) {
      ElMessage.success('实训课程与真实案例挂接创建成功');
      createDialogVisible.value = false;
      fetchCourses();
    }
  } catch (err) {
    console.error(err);
  } finally {
    savingCourse.value = false;
  }
};

onMounted(() => {
  fetchCourses();
});
</script>

<style scoped>
.training-view {
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

.main-card {
  min-height: calc(100vh - 200px);
}

.courses-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

@media (max-width: 1024px) {
  .courses-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .courses-grid {
    grid-template-columns: 1fr;
  }
}

.course-card {
  border-radius: 8px;
  display: flex;
  flex-direction: column;
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.hours-badge {
  font-size: 12px;
  color: #64748b;
}

.course-title {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #1e293b;
}

.course-desc {
  margin: 0 0 12px 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.course-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}

.profile-card {
  border-radius: 8px;
  text-align: center;
  padding: 10px 0;
}

.avatar-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.user-name {
  margin: 4px 0 0 0;
  font-size: 18px;
  color: #1e293b;
}

.user-role {
  margin: 0;
  display: flex;
  gap: 6px;
}

.profile-stats {
  display: flex;
  justify-content: space-around;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
}

.stat-lbl {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.text-success { color: #16a34a !important; }
.text-danger { color: #dc2626 !important; }

.history-card {
  border-radius: 8px;
}

.header-title {
  font-weight: 600;
  font-size: 15px;
}
</style>
