import { defineStore } from 'pinia';
import apiClient from '@/api/client';

export interface UserInfo {
  id: number;
  username: string;
  full_name: string;
  employee_no?: string;
  email?: string;
  role_code: string;
  work_type: string;
  force_change_password: boolean;
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('maintainwise_token') || '',
    userInfo: JSON.parse(localStorage.getItem('maintainwise_user') || 'null') as UserInfo | null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.userInfo?.role_code === 'ADMIN',
    isEngineer: (state) => state.userInfo?.role_code === 'ENGINEER',
    isSupervisor: (state) => state.userInfo?.role_code === 'SUPERVISOR',
    isTechnician: (state) => state.userInfo?.role_code === 'TECHNICIAN',
    canManageUsers: (state) => state.userInfo?.role_code === 'ADMIN',
    canManageEquipments: (state) => ['ADMIN', 'ENGINEER'].includes(state.userInfo?.role_code || ''),
    canManagePlans: (state) => ['ADMIN', 'ENGINEER'].includes(state.userInfo?.role_code || ''),
    canManageCourses: (state) => ['ADMIN', 'ENGINEER'].includes(state.userInfo?.role_code || ''),
    hasRole: (state) => (roles: string | string[]) => {
      const currentRole = state.userInfo?.role_code;
      if (!currentRole) return false;
      const roleList = Array.isArray(roles) ? roles : [roles];
      return roleList.includes(currentRole);
    },
    needsPasswordChange: (state) => state.userInfo?.force_change_password === true,
  },
  actions: {
    async login(loginForm: { username: string; password: string }) {
      const res = await apiClient.post<any, any>('/auth/login', loginForm);
      if ((res.code === 200 || res.code === 0) && res.data) {
        this.token = res.data.access_token;
        this.userInfo = {
          id: res.data.user_id,
          username: res.data.username,
          full_name: res.data.full_name,
          role_code: res.data.role_code,
          work_type: res.data.work_type,
          force_change_password: res.data.force_change_password,
        };
        localStorage.setItem('maintainwise_token', this.token);
        localStorage.setItem('maintainwise_user', JSON.stringify(this.userInfo));
      }
      return res;
    },
    async fetchProfile() {
      try {
        const res = await apiClient.get<any, any>('/auth/me');
        if ((res.code === 200 || res.code === 0) && res.data) {
          this.userInfo = res.data;
          localStorage.setItem('maintainwise_user', JSON.stringify(this.userInfo));
        }
      } catch (err) {
        console.error('Failed to fetch user profile:', err);
      }
    },
    async forceChangePassword(payload: { old_password: string; new_password: string }) {
      const res = await apiClient.post<any, any>('/auth/force-change-password', payload);
      if (res.code === 200 || res.code === 0) {
        if (this.userInfo) {
          this.userInfo.force_change_password = false;
          localStorage.setItem('maintainwise_user', JSON.stringify(this.userInfo));
        }
      }
      return res;
    },
    logout() {
      this.token = '';
      this.userInfo = null;
      localStorage.removeItem('maintainwise_token');
      localStorage.removeItem('maintainwise_user');
      window.location.href = '/login';
    },
  },
});
