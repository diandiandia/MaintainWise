import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';
import Layout from '@/components/Layout.vue';
import LoginView from '@/views/LoginView.vue';
import ForceChangePasswordView from '@/views/ForceChangePasswordView.vue';
import DashboardView from '@/views/DashboardView.vue';
import EquipmentListView from '@/views/EquipmentListView.vue';
import MaintenancePlanView from '@/views/MaintenancePlanView.vue';
import InspectionTouchView from '@/views/InspectionTouchView.vue';
import FaultKanbanView from '@/views/FaultKanbanView.vue';
import KnowledgeView from '@/views/KnowledgeView.vue';
import TrainingView from '@/views/TrainingView.vue';
import UserManagementView from '@/views/UserManagementView.vue';
import SystemSettingsView from '@/views/SystemSettingsView.vue';
import Error403View from '@/views/Error403View.vue';
import Error404View from '@/views/Error404View.vue';
import { setupRouterGuard } from './guard';

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
  },
  {
    path: '/force-change-password',
    name: 'ForceChangePassword',
    component: ForceChangePasswordView,
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: DashboardView,
      },
      {
        path: 'equipments',
        name: 'Equipments',
        component: EquipmentListView,
      },
      {
        path: 'maintenance',
        name: 'Maintenance',
        component: MaintenancePlanView,
      },
      {
        path: 'inspection',
        name: 'Inspection',
        component: InspectionTouchView,
      },
      {
        path: 'faults',
        name: 'Faults',
        component: FaultKanbanView,
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: KnowledgeView,
      },
      {
        path: 'training',
        name: 'Training',
        component: TrainingView,
      },
      {
        path: 'users',
        name: 'Users',
        component: UserManagementView,
        meta: { roles: ['ADMIN', 'SUPERVISOR'] },
      },
      {
        path: 'system',
        name: 'System',
        component: SystemSettingsView,
        meta: { roles: ['ADMIN'] },
      },
    ],
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: Error403View,
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: Error404View,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

setupRouterGuard(router);

export default router;
