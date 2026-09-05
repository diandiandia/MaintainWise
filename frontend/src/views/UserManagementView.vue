<template>
  <div class="users-view">
    <div class="page-header">
      <div class="header-titles">
        <h2>用户与班组工种权限管理</h2>
        <p>基于 RBAC 的角色与工种数据隔离、账号生命周期与密码重置 (SWR-USR-001/002/003)</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">创建新账号</el-button>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <div class="toolbar">
        <el-select v-model="filterRole" placeholder="按角色过滤" clearable style="width: 160px;" @change="fetchUsers">
          <el-option label="全部角色" value="" />
          <el-option label="系统管理员 (ADMIN)" value="ADMIN" />
          <el-option label="车间主管 (SUPERVISOR)" value="SUPERVISOR" />
          <el-option label="工程师 (ENGINEER)" value="ENGINEER" />
          <el-option label="技术员 (TECHNICIAN)" value="TECHNICIAN" />
        </el-select>
        <el-button :icon="Refresh" @click="fetchUsers">刷 新</el-button>
      </div>

      <el-table :data="users" v-loading="loading" border stripe style="margin-top: 14px;">
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="username" label="用户名" width="130" font-weight="600" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="role_code" label="系统角色" width="140">
          <template #default="{ row }">
            <el-tag :type="getRoleTag(row.role_code)">{{ row.role_code }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="work_type" label="专业工种" width="150">
          <template #default="{ row }">
            <el-tag type="info">{{ row.work_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="160" />
        <el-table-column prop="force_change_password" label="改密限制" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="row.force_change_password ? 'warning' : 'success'">
              {{ row.force_change_password ? '待改密' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="账号状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :disabled="row.role_code === 'ADMIN'"
              @change="(val) => handleToggleActive(row, val as boolean)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              link
              size="small"
              :disabled="row.role_code === 'ADMIN'"
              @click="handleDelete(row)"
            >
              软删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建用户弹窗 -->
    <el-dialog v-model="dialogVisible" title="创建系统用户" width="560px" append-to-body>
      <el-form ref="formRef" :model="form" :rules="formRules" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" placeholder="英文小写字母/数字" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="真实姓名" prop="full_name">
              <el-input v-model="form.full_name" placeholder="如: 张伟" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="工号" prop="employee_no">
              <el-input v-model="form.employee_no" placeholder="如: MW-012" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="电子邮箱" prop="email">
              <el-input v-model="form.email" placeholder="接收到期预警邮件" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="角色授权 (RBAC)" prop="role_code">
              <el-select v-model="form.role_code" style="width: 100%;">
                <el-option label="技术员 (TECHNICIAN)" value="TECHNICIAN" />
                <el-option label="工程师 (ENGINEER)" value="ENGINEER" />
                <el-option label="车间主管 (SUPERVISOR)" value="SUPERVISOR" />
                <el-option label="管理员 (ADMIN)" value="ADMIN" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="责任工种 (数据隔离)" prop="work_type">
              <el-select v-model="form.work_type" style="width: 100%;">
                <el-option label="机械工 (MECHANICAL)" value="MECHANICAL" />
                <el-option label="电气工 (ELECTRICAL)" value="ELECTRICAL" />
                <el-option label="自动化仪表 (INSTRUMENTATION)" value="INSTRUMENTATION" />
                <el-option label="通用全工种 (GENERAL)" value="GENERAL" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="初始密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="默认初始密码" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import apiClient from '@/api/client';
import { ElMessage, ElMessageBox, FormInstance } from 'element-plus';
import { Plus, Refresh } from '@element-plus/icons-vue';

const loading = ref(false);
const users = ref<any[]>([]);
const filterRole = ref('');

const dialogVisible = ref(false);
const saving = ref(false);
const formRef = ref<FormInstance>();
const form = reactive({
  username: '',
  full_name: '',
  employee_no: '',
  email: '',
  role_code: 'TECHNICIAN',
  work_type: 'MECHANICAL',
  password: 'User@2026!',
});

const formRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  full_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  employee_no: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
};

const getRoleTag = (r?: string) => {
  switch (r) {
    case 'ADMIN': return 'danger';
    case 'SUPERVISOR': return 'warning';
    case 'ENGINEER': return 'primary';
    case 'TECHNICIAN': return 'success';
    default: return 'info';
  }
};

const fetchUsers = async () => {
  loading.value = true;
  try {
    let url = `/users?limit=50`;
    if (filterRole.value) url += `&role_code=${filterRole.value}`;
    const res = await apiClient.get<any, any>(url);
    if (res.code === 200 && res.data?.items) {
      users.value = res.data.items;
    }
  } catch (err) {
    console.error(err);
  } finally {
    loading.value = false;
  }
};

const openCreateDialog = () => {
  dialogVisible.value = true;
};

const submitCreate = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    saving.value = true;
    try {
      const res = await apiClient.post<any, any>('/users', form);
      if (res.code === 200) {
        ElMessage.success('用户创建成功，已默认开启首次登录强制改密限制');
        dialogVisible.value = false;
        fetchUsers();
      }
    } catch (err) {
      console.error(err);
    } finally {
      saving.value = false;
    }
  });
};

const handleToggleActive = async (row: any, val: boolean) => {
  try {
    const res = await apiClient.put<any, any>(`/users/${row.id}`, { is_active: val });
    if (res.code === 200) {
      ElMessage.success(`用户状态已更新为: ${val ? '已启用' : '已禁用'}`);
    }
  } catch (err) {
    row.is_active = !val;
  }
};

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(`确认删除用户【${row.full_name}】？`, '警告', { type: 'warning' });
    const res = await apiClient.delete<any, any>(`/users/${row.id}`);
    if (res.code === 200) {
      ElMessage.success('用户已软删除');
      fetchUsers();
    }
  } catch (err) {
    // Cancelled
  }
};

onMounted(() => {
  fetchUsers();
});
</script>

<style scoped>
.users-view {
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

.table-card {
  min-height: calc(100vh - 200px);
}

.toolbar {
  display: flex;
  gap: 12px;
}
</style>
