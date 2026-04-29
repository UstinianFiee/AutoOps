import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '仪表盘' } },
      { path: 'servers', name: 'Servers', component: () => import('@/views/Servers.vue'), meta: { title: '服务器管理' } },
      { path: 'apps', name: 'Apps', component: () => import('@/views/Apps.vue'), meta: { title: '应用管理' } },
      { path: 'containers', name: 'Containers', component: () => import('@/views/Containers.vue'), meta: { title: '容器管理' } },
      { path: 'deploy', name: 'Deploy', component: () => import('@/views/Deploy.vue'), meta: { title: 'CI/CD 部署' } },
      { path: 'monitor', name: 'Monitor', component: () => import('@/views/Monitor.vue'), meta: { title: '监控告警' } },
      { path: 'logs', name: 'Logs', component: () => import('@/views/Logs.vue'), meta: { title: '日志查询' } },
      { path: 'tasks', name: 'Tasks', component: () => import('@/views/Tasks.vue'), meta: { title: 'Ansible 任务' } },
      { path: 'users', name: 'Users', component: () => import('@/views/Users.vue'), meta: { title: '用户管理' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return '/login'
  }
})

export default router
