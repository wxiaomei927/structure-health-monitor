import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue')
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/LoginView.vue')
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { title: '监测总览' }
  },
  {
    path: '/zone',
    name: 'Zone',
    component: () => import('../views/ZoneView.vue'),
    meta: { title: '区域监测' }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/HistoryView.vue'),
    meta: { title: '历史数据' }
  },
  {
    path: '/alerts',
    name: 'Alerts',
    component: () => import('../views/AlertsView.vue'),
    meta: { title: '异常告警' }
  },
  {
    path: '/devices',
    name: 'Devices',
    component: () => import('../views/DeviceView.vue'),
    meta: { title: '设备管理' }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 未登录时统一挡到登录页
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const authPages = ['Login', 'Register']
  if (!authPages.includes(to.name) && !token) {
    next({ name: 'Login' })
    return
  }
  if (authPages.includes(to.name) && token) {
    next({ name: 'Dashboard' })
    return
  }
  next()
})

export default router
