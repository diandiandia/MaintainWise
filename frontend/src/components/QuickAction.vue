<template>
  <div class="quick-action-container">
    <el-button
      type="primary"
      size="large"
      circle
      class="fab-btn"
      @click="toggleMenu"
    >
      <el-icon :size="24"><Plus /></el-icon>
    </el-button>

    <transition name="el-zoom-in-bottom">
      <div v-if="visible" class="fab-menu">
        <el-card shadow="always" class="fab-card">
          <div class="fab-item" @click="handleQuickFault">
            <el-icon color="#f56c6c"><WarningFilled /></el-icon>
            <span>快速故障报修</span>
          </div>
          <div class="fab-item" @click="handleQuickInspection">
            <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
            <span>快速巡检打卡</span>
          </div>
          <div class="fab-item" @click="handleQuickKnowledge">
            <el-icon color="#409eff"><Search /></el-icon>
            <span>排查知识检索</span>
          </div>
        </el-card>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { Plus, WarningFilled, CircleCheckFilled, Search } from '@element-plus/icons-vue';

const router = useRouter();
const visible = ref(false);

const emit = defineEmits<{
  (e: 'quick-fault'): void;
  (e: 'quick-knowledge'): void;
}>();

const toggleMenu = () => {
  visible.value = !visible.value;
};

const handleQuickFault = () => {
  visible.value = false;
  router.push('/faults?action=create');
};

const handleQuickInspection = () => {
  visible.value = false;
  router.push('/inspection');
};

const handleQuickKnowledge = () => {
  visible.value = false;
  router.push('/knowledge');
};
</script>

<style scoped>
.quick-action-container {
  position: fixed;
  right: 28px;
  bottom: 32px;
  z-index: 1999;
}

.fab-btn {
  width: 58px;
  height: 58px;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.4);
  font-size: 24px;
  transition: transform 0.3s;
}

.fab-btn:hover {
  transform: scale(1.08);
}

.fab-menu {
  position: absolute;
  right: 0;
  bottom: 68px;
  width: 200px;
}

.fab-card :deep(.el-card__body) {
  padding: 10px;
}

.fab-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  cursor: pointer;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  transition: background-color 0.2s;
}

.fab-item:hover {
  background-color: #f0f7ff;
}
</style>
