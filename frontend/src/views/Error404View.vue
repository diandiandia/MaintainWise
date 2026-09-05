<template>
  <div class="error-page">
    <el-result
      icon="error"
      title="404 - 页面未找到"
      sub-title="抱歉，您访问的工业维保页面不存在或已被移除。"
    >
      <template #extra>
        <el-button type="primary" @click="$router.push('/dashboard')">返回工作台</el-button>
      </template>
    </el-result>
  </div>
</template>

<style scoped>
.error-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
}
</style>
