<template>
  <el-container class="app-wrapper">
    <!-- 侧边栏导航 -->
    <el-aside width="240px" class="aside-menu">
      <div class="logo-area">
        <el-icon :size="28" color="#409EFF"><Tools /></el-icon>
        <span class="logo-title">MaintainWise</span>
      </div>

      <el-menu
        :default-active="activeRoute"
        class="el-menu-vertical"
        router
        background-color="#001529"
        text-color="#a6adb4"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>综合运营大盘</span>
        </el-menu-item>

        <el-menu-item index="/equipments">
          <el-icon><Cpu /></el-icon>
          <span>设备台账资产</span>
        </el-menu-item>

        <el-menu-item index="/maintenance">
          <el-icon><Calendar /></el-icon>
          <span>维护计划与工单</span>
        </el-menu-item>

        <el-menu-item index="/inspection">
          <el-icon><Checked /></el-icon>
          <span>现场巡检打卡</span>
        </el-menu-item>

        <el-menu-item index="/faults">
          <el-icon><WarnTriangleFilled /></el-icon>
          <span>故障流转看板</span>
        </el-menu-item>

        <el-menu-item index="/knowledge">
          <el-icon><Reading /></el-icon>
          <span>故障排查知识库</span>
        </el-menu-item>

        <el-menu-item index="/training">
          <el-icon><School /></el-icon>
          <span>技能实训与档案</span>
        </el-menu-item>

        <el-menu-item v-if="authStore.isSupervisor" index="/users">
          <el-icon><UserFilled /></el-icon>
          <span>用户与班组管理</span>
        </el-menu-item>

        <el-menu-item v-if="authStore.isAdmin" index="/system">
          <el-icon><Setting /></el-icon>
          <span>系统设置与审计</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主体区域 -->
    <el-container class="main-container">
      <!-- 顶部 Header -->
      <el-header class="app-header">
        <div class="header-left">
          <span class="header-breadcrumb">智能制造设备全生命周期维保协同平台</span>
        </div>

        <div class="header-right">
          <el-tag :type="getRoleTagType(authStore.userInfo?.role_code)" effect="dark" size="small">
            {{ getRoleLabel(authStore.userInfo?.role_code) }}
          </el-tag>
          <el-tag type="info" size="small">
            工种: {{ authStore.userInfo?.work_type || '通用' }}
          </el-tag>

          <el-dropdown trigger="click" @command="handleUserCommand">
            <span class="user-profile-btn">
              <el-avatar size="small" style="background-color: #409eff;">
                {{ authStore.userInfo?.full_name?.charAt(0) || 'U' }}
              </el-avatar>
              <span class="username">{{ authStore.userInfo?.full_name || authStore.userInfo?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">工号: {{ authStore.userInfo?.employee_no || 'MW-001' }}</el-dropdown-item>
                <el-dropdown-item command="change-pwd">安全改密</el-dropdown-item>
                <el-dropdown-item divided command="logout" style="color: #f56c6c;">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 视图内容渲染区 -->
      <el-main class="app-main-content">
        <router-view />
      </el-main>

      <!-- 全局悬浮高频快捷操作按钮 (SWR-DSH-004) -->
      <QuickAction />
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import QuickAction from '@/components/QuickAction.vue';
import {
  Tools,
  DataAnalysis,
  Cpu,
  Calendar,
  Checked,
  WarnTriangleFilled,
  Reading,
  School,
  UserFilled,
  Setting,
  ArrowDown,
} from '@element-plus/icons-vue';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const activeRoute = computed(() => route.path);

const getRoleLabel = (role?: string) => {
  switch (role) {
    case 'ADMIN': return '系统管理员';
    case 'SUPERVISOR': return '车间主管';
    case 'TECHNICIAN': return '维保技术员';
    default: return '用户';
  }
};

const getRoleTagType = (role?: string) => {
  switch (role) {
    case 'ADMIN': return 'danger';
    case 'SUPERVISOR': return 'warning';
    case 'TECHNICIAN': return 'success';
    default: return 'info';
  }
};

const handleUserCommand = (command: string) => {
  if (command === 'logout') {
    authStore.logout();
  } else if (command === 'change-pwd') {
    router.push('/force-change-password');
  }
};
</script>

<style scoped>
.app-wrapper {
  min-height: 100vh;
  display: flex;
}

.aside-menu {
  background-color: #001529;
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.35);
  display: flex;
  flex-direction: column;
}

.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  background-color: #002140;
}

.logo-title {
  color: #ffffff;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.el-menu-vertical {
  border-right: none;
  flex: 1;
}

.main-container {
  display: flex;
  flex-direction: column;
  background-color: #f0f2f5;
  min-width: 0;
}

.app-header {
  height: 60px;
  background-color: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-breadcrumb {
  font-size: 15px;
  color: #606266;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-profile-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.user-profile-btn:hover {
  background-color: #f5f7fa;
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.app-main-content {
  padding: 20px;
  overflow-y: auto;
}
</style>
