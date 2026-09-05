<template>
  <div class="error-page">
    <el-result
      icon="warning"
      title="403 - 访问受限"
      sub-title="您当前的角色权限无法访问该功能模块，请联系系统管理员进行工种与角色提权。"
    >
      <template #extra>
        <el-button type="primary" @click="$router.push('/dashboard')">返回综合大盘</el-button>
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
