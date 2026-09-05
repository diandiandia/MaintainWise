<template>
  <div class="force-pwd-page">
    <div class="force-pwd-card">
      <div class="security-banner">
        <el-icon :size="48" color="#e6a23c"><Lock /></el-icon>
        <h2>安全策略提醒：必须修改初始密码</h2>
        <p>根据工业安全合规标准 (SWR-USR-004)，首次登录或密码重置后必须设置新密码方可进入系统。</p>
      </div>

      <el-card shadow="always" class="form-card">
        <el-form
          ref="formRef"
          :model="formData"
          :rules="formRules"
          label-position="top"
          @submit.prevent="handleSubmit"
        >
          <el-form-item label="当前原密码" prop="old_password">
            <el-input
              v-model="formData.old_password"
              type="password"
              placeholder="请输入当前密码"
              show-password
              size="large"
            />
          </el-form-item>

          <el-form-item label="设置新密码" prop="new_password">
            <el-input
              v-model="formData.new_password"
              type="password"
              placeholder="至少8位，包含大小写字母及数字/特殊符号"
              show-password
              size="large"
            />
          </el-form-item>

          <el-form-item label="确认新密码" prop="confirm_password">
            <el-input
              v-model="formData.confirm_password"
              type="password"
              placeholder="请再次输入新密码"
              show-password
              size="large"
            />
          </el-form-item>

          <div class="pwd-requirements">
            <p>密码强度要求：</p>
            <ul>
              <li :class="{ valid: formData.new_password.length >= 8 }">长度至少 8 个字符</li>
              <li :class="{ valid: /[A-Z]/.test(formData.new_password) && /[a-z]/.test(formData.new_password) }">包含大小写英文字母</li>
              <li :class="{ valid: /[0-9]/.test(formData.new_password) || /[^A-Za-z0-9]/.test(formData.new_password) }">包含数字或特殊符号</li>
              <li :class="{ valid: formData.new_password && formData.new_password === formData.confirm_password }">两次输入的密码一致</li>
            </ul>
          </div>

          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-btn"
            @click="handleSubmit"
          >
            确认修改并进入系统
          </el-button>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { ElMessage, FormInstance } from 'element-plus';
import { Lock } from '@element-plus/icons-vue';

const router = useRouter();
const authStore = useAuthStore();
const formRef = ref<FormInstance>();
const loading = ref(false);

const formData = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
});

const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (value !== formData.new_password) {
    callback(new Error('两次输入的新密码不一致'));
  } else {
    callback();
  }
};

const formRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度不得小于8位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
};

const handleSubmit = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      const res = await authStore.forceChangePassword({
        old_password: formData.old_password,
        new_password: formData.new_password,
      });

      if (res.code === 200) {
        ElMessage.success('密码修改成功，安全限制已解除');
        router.push('/dashboard');
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
.force-pwd-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f2f5;
  padding: 20px;
}

.force-pwd-card {
  width: 100%;
  max-width: 520px;
}

.security-banner {
  text-align: center;
  margin-bottom: 24px;
}

.security-banner h2 {
  margin: 12px 0 8px 0;
  color: #1e293b;
  font-size: 22px;
}

.security-banner p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
}

.form-card {
  border-radius: 10px;
}

.pwd-requirements {
  background-color: #f8fafc;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 13px;
}

.pwd-requirements p {
  margin: 0 0 6px 0;
  font-weight: 600;
  color: #475569;
}

.pwd-requirements ul {
  margin: 0;
  padding-left: 20px;
  color: #94a3b8;
}

.pwd-requirements li.valid {
  color: #16a34a;
  font-weight: 500;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
}
</style>
