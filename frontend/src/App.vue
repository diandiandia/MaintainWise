<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import zhCn from 'element-plus/es/locale/lang/zh-cn';

const IDLE_TIMEOUT_MS = 30 * 60 * 1000; // 30分钟无操作自动登出
const authStore = useAuthStore();
const router = useRouter();

let idleTimer: ReturnType<typeof setTimeout> | null = null;

function resetIdleTimer() {
  if (!authStore.isAuthenticated) return;
  if (idleTimer) clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    authStore.logout();
  }, IDLE_TIMEOUT_MS);
}

function handleUserActivity() {
  resetIdleTimer();
}

onMounted(() => {
  if (authStore.isAuthenticated) {
    resetIdleTimer();
    const events = ['mousemove', 'keydown', 'click', 'touchstart', 'scroll'];
    events.forEach((event) => {
      window.addEventListener(event, handleUserActivity);
    });
  }
});

onUnmounted(() => {
  if (idleTimer) clearTimeout(idleTimer);
  const events = ['mousemove', 'keydown', 'click', 'touchstart', 'scroll'];
  events.forEach((event) => {
    window.removeEventListener(event, handleUserActivity);
  });
});
</script>

<style>
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
}
</style>