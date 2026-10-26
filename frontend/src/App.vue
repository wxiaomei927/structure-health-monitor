<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN">
    <n-message-provider>
      <n-dialog-provider>
        <n-loading-bar-provider>
          <div class="app-shell">
            <!-- 登录页独立全屏，不带顶栏与导航 -->
            <router-view v-if="isLoginPage" />

            <template v-else>
              <!-- 顶栏：品牌 + 主导航 + 账号 -->
              <header class="app-header">
                <div class="header-left">
                  <div class="brand">
                    <span class="brand-mark">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22">
                        <path fill="currentColor" d="M2 13.5l3.2-4.4 3 3.4 3.6-5.6 3.4 5 2.4-2.6L22 13H2z"/>
                        <path fill="currentColor" d="M2 16h20v2H2z"/>
                      </svg>
                    </span>
                    <span class="brand-name">结构健康监测平台</span>
                  </div>
                  <nav class="main-nav">
                    <router-link
                      v-for="item in navItems"
                      :key="item.key"
                      :to="item.path"
                      class="nav-item"
                      :class="{ 'nav-item-active': route.name === item.key }"
                    >
                      {{ item.label }}
                    </router-link>
                  </nav>
                </div>

                <div class="header-right">
                  <n-dropdown :options="userOptions" @select="handleUserAction">
                    <button class="user-trigger">
                      <span class="user-initial">{{ userInitial }}</span>
                      <span class="user-name">{{ displayName }}</span>
                      <n-icon :size="14"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></svg></n-icon>
                    </button>
                  </n-dropdown>
                </div>
              </header>

              <main class="app-main">
                <router-view v-slot="{ Component }">
                  <transition name="fade" mode="out-in">
                    <component :is="Component" />
                  </transition>
                </router-view>
              </main>
            </template>
          </div>
        </n-loading-bar-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import { zhCN } from 'naive-ui'
import { authApi } from './api'

const route = useRoute()
const router = useRouter()

const displayName = ref(localStorage.getItem('display_name') || '')

const isLoginPage = computed(() => ['Login', 'Register'].includes(route.name))

const navItems = [
  { key: 'Dashboard', label: '监测总览', path: '/' },
  { key: 'Zone', label: '区域监测', path: '/zone' },
  { key: 'History', label: '历史数据', path: '/history' },
  { key: 'Alerts', label: '异常告警', path: '/alerts' },
  { key: 'Devices', label: '设备管理', path: '/devices' }
]

const themeOverrides = {
  common: {
    primaryColor: '#165DFF',
    primaryColorHover: '#4080FF',
    primaryColorPressed: '#0E42D2',
    primaryColorSuppl: '#165DFF',
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
    fontFamilyMono: '"SF Mono", "JetBrains Mono", Consolas, monospace',
    borderRadius: '8px',
    // 组件库内部的小字统一放大，naive-ui 默认的 12px 在笔记本上偏小
    fontSize: '15px',
    fontSizeSmall: '14px',
    textColor1: '#1D2129',
    textColor2: '#4E5969',
    textColor3: '#86909C',
    borderColor: '#E5E6EB',
    dividerColor: '#F2F3F5',
    bodyColor: '#f5f7fa',
    cardColor: '#ffffff'
  },
  Card: {
    borderRadius: '12px',
    borderColor: 'rgba(0, 0, 0, 0.04)',
    color: '#ffffff',
    titleFontSizeMedium: '17px'
  },
  Tag: {
    fontSizeSmall: '14px'
  },
  Button: {
    fontSizeSmall: '14px',
    fontSizeMedium: '15px'
  },
  DataTable: {
    thColor: '#f7f8fa',
    thTextColor: '#86909C',
    thFontSize: '14px',
    tdColorHover: '#f7f8fa',
    borderColor: '#f2f3f5',
    fontSize: '14px'
  },
  Menu: {
    itemColorHover: '#f2f3f5',
    itemColorActive: '#e8f3ff',
    itemTextColorActive: '#165DFF',
    itemHeight: '52px'
  }
}

const userOptions = [{ label: '退出登录', key: 'logout' }]

const userInitial = computed(() => (displayName.value || 'A').charAt(0))

function handleUserAction(key) {
  if (key !== 'logout') return
  localStorage.removeItem('access_token')
  localStorage.removeItem('username')
  localStorage.removeItem('display_name')
  router.push({ name: 'Login' })
}

// App.vue 在登录前就已挂载，登录后组件不会重新挂载，
// 所以要盯着路由变化，从登录页切进主界面时刷新一次用户信息
watch(
  () => route.name,
  (name) => {
    if (!name || name === 'Login' || name === 'Register') return
    if (!localStorage.getItem('access_token')) return
    authApi.me()
      .then((info) => {
        if (info?.display_name) {
          displayName.value = info.display_name
          localStorage.setItem('display_name', info.display_name)
        }
      })
      .catch(() => {})
  },
  { immediate: true }
)
</script>

<style scoped>
.app-shell {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-header {
  height: var(--header-height);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-8);
  background: var(--surface);
  box-shadow: var(--shadow-header);
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-8);
  min-width: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
  min-width: 240px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-panel);
  background: linear-gradient(135deg, var(--accent) 0%, #4080ff 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-name {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: 1px;
  white-space: nowrap;
}

/* 主导航：下划线指示选中，不做色块背景 */
.main-nav {
  display: flex;
  align-items: stretch;
  height: var(--header-height);
  gap: var(--space-1);
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 0 var(--space-5);
  font-size: 18px;
  font-weight: 500;
  color: var(--ink-700);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: color var(--transition-fast), border-color var(--transition-fast);
  white-space: nowrap;
}

.nav-item:hover {
  color: var(--ink-900);
}

.nav-item-active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-shrink: 0;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: none;
  border-radius: var(--radius-control);
  cursor: pointer;
  font-family: inherit;
  transition: background-color var(--transition-fast);
}

.user-trigger:hover {
  background: rgba(0, 0, 0, 0.04);
}

.user-initial {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: var(--text-sm);
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--ink-900);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  background: #f5f7fa;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 300ms ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
