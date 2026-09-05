import type { Directive, DirectiveBinding } from 'vue';
import { useAuthStore } from '@/stores/auth';

/**
 * 按钮与元素级角色权限控制指令 (SWR-USR-001)
 * 未授权的角色直接移除 DOM 节点，避免非法点击和 403 权限不足提示
 * 用法:
 *   <el-button v-permission="['ADMIN', 'ENGINEER']">录入设备</el-button>
 *   <el-button v-permission="'ADMIN'">危险操作</el-button>
 */
export const permissionDirective: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    const { value } = binding;
    const authStore = useAuthStore();
    const userRole = authStore.userInfo?.role_code;

    if (value) {
      const allowedRoles = Array.isArray(value) ? value : [value];
      const hasPermission = !!userRole && allowedRoles.includes(userRole);

      if (!hasPermission) {
        // 直接从父节点中移除 DOM，彻底对无权限角色关闭该功能与入口
        el.parentNode?.removeChild(el);
      }
    } else {
      throw new Error("v-permission 指令必须指定允许的角色数组，例如 v-permission=\"['ADMIN', 'ENGINEER']\"");
    }
  },
};
