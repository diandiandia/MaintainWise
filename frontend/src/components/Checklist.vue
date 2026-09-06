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
      width="640px"
      append-to-body
    >
      <div class="sop-dialog-content">
        <!-- 状态栏与上传操作 -->
        <div class="sop-toolbar">
          <div class="sop-source-badge">
            <el-tag :type="item.standard_photo_url ? 'success' : 'info'" size="small">
              {{ item.standard_photo_url ? '现场实拍标准图已就绪' : '系统通用 SOP 示范图 (未上传实拍)' }}
            </el-tag>
          </div>
          <el-upload
            :show-file-list="false"
            :http-request="handleUploadSopPhoto"
            accept="image/*"
          >
            <el-button size="small" type="primary" plain :icon="Upload" :loading="uploading">
              {{ item.standard_photo_url ? '更换标准图示' : '上传现场合格标准图' }}
            </el-button>
          </el-upload>
        </div>

        <!-- 图像展示区域 -->
        <div class="sop-image-box">
          <template v-if="item.standard_photo_url">
            <el-image
              :src="item.standard_photo_url"
              alt="SOP 标准图示"
              class="sop-image"
              :preview-src-list="[item.standard_photo_url]"
              preview-teleported
              fit="contain"
            >
              <template #error>
                <div class="image-fallback-box">
                  <el-icon :size="32" color="#909399"><PictureFilled /></el-icon>
                  <span>图片加载失败，请重新上传现场照片</span>
                </div>
              </template>
            </el-image>
          </template>
          <template v-else>
            <!-- 内网离线纯 SVG 工业标准示意图 -->
            <div class="svg-sop-placeholder">
              <svg viewBox="0 0 400 180" class="sop-svg-diagram">
                <rect width="400" height="180" rx="8" fill="#f8fafc" />
                <!-- 仪表盘/电机设备示意图形 -->
                <circle cx="110" cy="90" r="55" fill="#f1f5f9" stroke="#94a3b8" stroke-width="2" />
                <path d="M 75 90 A 35 35 0 0 1 145 90" fill="none" stroke="#22c55e" stroke-width="6" />
                <line x1="110" y1="90" x2="135" y2="68" stroke="#0284c7" stroke-width="3" stroke-linecap="round" />
                <circle cx="110" cy="90" r="5" fill="#1e293b" />
                <text x="110" y="48" text-anchor="middle" font-size="11" fill="#16a34a" font-weight="bold">标准合格区间</text>
                <!-- 说明与导引 -->
                <rect x="195" y="35" width="185" height="110" rx="6" fill="#ffffff" stroke="#cbd5e1" />
                <text x="210" y="60" font-size="12" fill="#1e293b" font-weight="bold">SOP 现场比对规范</text>
                <text x="210" y="85" font-size="11" fill="#64748b">1. 状态/读数必须处于合格刻度</text>
                <text x="210" y="105" font-size="11" fill="#64748b">2. 部件外观整洁无裂纹渗油</text>
                <text x="210" y="125" font-size="11" fill="#64748b">3. 紧固件与防松标记对齐无位移</text>
              </svg>
              <div class="placeholder-tip">
                <el-icon><InfoFilled /></el-icon>
                <span>未配置实物照片，现展示离线通用示意图。可点击右上角随时上传现场实拍照片。</span>
              </div>
            </div>
          </template>
        </div>

        <div class="sop-guidelines">
          <h4>合格判定规范：</h4>
          <p>{{ item.criteria || '设备运行平稳，指示灯正常常亮，接口处无漏油/漏气。' }}</p>
          <div v-if="item.method">
            <h4>检查方法与工具：</h4>
            <p>{{ item.method }}</p>
          </div>
          <h4>现场作业注意要点：</h4>
          <ul>
            <li>请穿戴绝缘手套与防护装备进行现场比对与触检。</li>
            <li>若发现读数偏差超过允许阈值或有裂纹/异常温升，必须立即拍照留存并置为“异常”。</li>
          </ul>
        </div>
      </div>
      <template #footer>
        <el-button @click="showSopDialog = false">关 闭</el-button>
        <el-button type="primary" @click="showSopDialog = false">我已了解标准</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Picture, Upload, PictureFilled, InfoFilled } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import apiClient from '@/api/client';

interface ChecklistItem {
  id?: number;
  plan_item_id?: number;
  item_name: string;
  is_required?: boolean;
  criteria?: string;
  method?: string;
  standard_photo_url?: string;
}

const props = defineProps<{
  item: ChecklistItem;
  index: number;
}>();

const showSopDialog = ref(false);
const uploading = ref(false);

const handleUploadSopPhoto = async (options: any) => {
  const file = options.file;
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('file_tag', 'SOP');

  uploading.value = true;
  try {
    const res = await apiClient.post<any, any>('/system/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    const url = res.data?.url;
    if (url) {
      props.item.standard_photo_url = url;
      ElMessage.success('SOP 标准图示已成功上传并生效！');
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '上传 SOP 标准照片失败');
  } finally {
    uploading.value = false;
  }
};
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

.sop-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sop-image-box {
  width: 100%;
  min-height: 220px;
  max-height: 300px;
  background-color: #f8fafc;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sop-image {
  width: 100%;
  height: 260px;
  border-radius: 6px;
}

.image-fallback-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 200px;
  color: #909399;
  font-size: 13px;
}

.svg-sop-placeholder {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 16px;
}

.sop-svg-diagram {
  width: 100%;
  max-width: 400px;
  height: auto;
}

.placeholder-tip {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-size: 12px;
}

.sop-guidelines h4 {
  margin: 10px 0 4px 0;
  color: #1e293b;
  font-size: 14px;
}

.sop-guidelines p,
.sop-guidelines ul {
  margin: 0;
  padding-left: 20px;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}
</style>
