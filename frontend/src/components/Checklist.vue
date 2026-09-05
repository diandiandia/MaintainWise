<template>
  <div class="checklist-item-card">
    <div class="item-header">
      <div class="item-meta">
        <span class="item-seq">#{{ index + 1 }}</span>
        <span class="item-title">{{ item.item_name }}</span>
        <el-tag size="small" :type="item.is_required ? 'danger' : 'info'">
          {{ item.is_required ? '必检项' : '选检项' }}
        </el-tag>
      </div>
      <el-button
        type="primary"
        link
        size="small"
        @click="showSopDialog = true"
        class="sop-btn"
      >
        <el-icon><Picture /></el-icon>
        SOP标准图示
      </el-button>
    </div>

    <div class="item-body">
      <div class="sop-standard-text">
        <span class="label">判定标准：</span>
        <span>{{ item.criteria || '表面无渗漏，运转无异响，紧固件无松脱' }}</span>
      </div>
      <div v-if="item.method" class="sop-method-text">
        <span class="label">检查方法：</span>
        <span>{{ item.method }}</span>
      </div>
    </div>

    <!-- SOP 标准图示比对弹窗 (SWR-MNT-002) -->
    <el-dialog
      v-model="showSopDialog"
      :title="`SOP 标准图示与比对规范 - ${item.item_name}`"
      width="600px"
      append-to-body
    >
      <div class="sop-dialog-content">
        <div class="sop-image-box">
          <img
            :src="item.standard_photo_url || defaultSopPhoto"
            alt="SOP 标准图示"
            class="sop-image"
          />
        </div>
        <div class="sop-guidelines">
          <h4>合格判定规范：</h4>
          <p>{{ item.criteria || '设备运行平稳，指示灯正常常亮，接口处无漏油/漏气。' }}</p>
          <h4>检查注意要点：</h4>
          <ul>
            <li>请戴好绝缘手套与护目镜进行现场比对。</li>
            <li>若发现读数偏差超过允许阈值或有裂纹，必须立即拍照留存并置为“异常”。</li>
          </ul>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="showSopDialog = false">我已了解标准</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Picture } from '@element-plus/icons-vue';

interface ChecklistItem {
  id?: number;
  item_name: string;
  is_required?: boolean;
  criteria?: string;
  method?: string;
  standard_photo_url?: string;
}

defineProps<{
  item: ChecklistItem;
  index: number;
}>();

const showSopDialog = ref(false);
const defaultSopPhoto = 'https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=600&auto=format&fit=crop&q=80';
</script>

<style scoped>
.checklist-item-card {
  padding: 14px 18px;
  background-color: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.item-seq {
  font-weight: 700;
  color: #909399;
  font-size: 14px;
}

.item-title {
  font-weight: 600;
  font-size: 16px;
  color: #303133;
}

.sop-btn {
  font-size: 14px;
}

.item-body {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.label {
  font-weight: 500;
  color: #409eff;
}

.sop-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sop-image-box {
  width: 100%;
  height: 260px;
  background-color: #f5f7fa;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sop-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: cover;
}

.sop-guidelines h4 {
  margin: 8px 0 4px 0;
  color: #303133;
}

.sop-guidelines p, .sop-guidelines ul {
  margin: 0;
  padding-left: 20px;
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
}
</style>
