import { Router } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

export function setupRouterGuard(router: Router) {
  router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore();

    if (to.path === '/login') {
      if (authStore.isAuthenticated) {
        return next('/dashboard');
      }
      return next();
    }

    // 1. 登录凭据检查
    if (!authStore.isAuthenticated) {
      return next({ path: '/login', query: { redirect: to.fullPath } });
    }

    // 2. 强制改密严格阻断 (REQ-USR-004 / SWR-USR-004)
    if (authStore.needsPasswordChange) {
      if (to.path !== '/force-change-password') {
        return next('/force-change-password');
      }
      return next(); // 放行改密页面
    }

    // 已改密用户无需重复进入改密页
    if (to.path === '/force-change-password' && !authStore.needsPasswordChange) {
      return next('/dashboard');
    }

    // 3. 角色权限拦截 (RBAC)
    if (to.meta?.roles) {
      const allowedRoles = to.meta.roles as string[];
      const userRole = authStore.userInfo?.role_code;
      if (!userRole || !allowedRoles.includes(userRole)) {
        return next('/403');
      }
    }

    next();
  });
}
