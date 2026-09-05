<template>
  <div class="login-page">
    <div class="login-card-wrapper">
      <div class="login-header">
        <el-icon :size="42" color="#409eff"><Tools /></el-icon>
        <h1 class="brand-title">MaintainWise</h1>
        <p class="brand-subtitle">离散制造企业综合设备维保协同系统</p>
      </div>

      <el-card shadow="always" class="login-box">
        <h2 class="form-title">系统安全登录</h2>

        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          label-position="top"
          @keyup.enter="handleLogin"
        >
          <el-form-item label="用户名 / 工号" prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="请输入用户名"
              size="large"
              :prefix-icon="User"
              clearable
            />
          </el-form-item>

          <el-form-item label="登录密码" prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <div class="quick-credentials">
            <span class="label">测试快速填充：</span>
            <el-button size="small" link type="primary" @click="fillAccount('admin', 'MaintainWiseAdmin@2026')">系统管理员 (admin)</el-button>
          </div>

          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-btn"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form>
      </el-card>

      <div class="login-footer">
        <p>© 2026 MaintainWise Inc. 工业互联网与智能维保标准体系</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { ElMessage, FormInstance } from 'element-plus';
import { Tools, User, Lock } from '@element-plus/icons-vue';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const loginFormRef = ref<FormInstance>();
const loading = ref(false);

const loginForm = reactive({
  username: 'admin',
  password: '',
});

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
};

const fillAccount = (u: string, p: string) => {
  loginForm.username = u;
  loginForm.password = p;
};

const handleLogin = async () => {
  if (!loginFormRef.value) return;
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      const res = await authStore.login({
        username: loginForm.username,
        password: loginForm.password,
      });

      if (res.code === 200 || res.code === 0) {
        ElMessage.success('登录成功');
        if (res.data?.force_change_password) {
          ElMessage.warning('首次登录或重置，请立即修改密码以保障账号安全');
          router.push('/force-change-password');
        } else {
          const redirect = (route.query.redirect as string) || '/dashboard';
          router.push(redirect);
        }
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      loading.value = false;
    }
  });
};
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0b1d3a 0%, #1a365d 50%, #2b6cb0 100%);
  padding: 20px;
}

.login-card-wrapper {
  width: 100%;
  max-width: 440px;
}

.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.brand-title {
  margin: 12px 0 6px 0;
  font-size: 28px;
  color: #ffffff;
  letter-spacing: 1px;
}

.brand-subtitle {
  margin: 0;
  font-size: 14px;
  color: #cbd5e1;
}

.login-box {
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
  background: #ffffff;
}

.form-title {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  text-align: center;
}

.quick-credentials {
  margin: -8px 0 18px 0;
  font-size: 12px;
  color: #64748b;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
}

.login-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 12px;
  color: #94a3b8;
}
</style>
