<template>
  <div class="layout">
    <!-- 侧边栏 -->
    <aside :class="['sidebar', { collapsed }]">
      <!-- Logo -->
      <div class="sidebar-logo">
        <div class="logo-icon">
          <img src="/autoops.png" width="32" height="32" style="border-radius:8px;object-fit:contain;display:block" alt="AutoOps"/>
        </div>
        <transition name="fade-x">
          <span v-if="!collapsed" class="logo-text">AutoOps</span>
        </transition>
      </div>

      <!-- 菜单 -->
      <nav class="sidebar-nav">
        <div class="nav-section-label" v-if="!collapsed">主要功能</div>
        <router-link
          v-for="item in mainMenu"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
          :title="collapsed ? item.label : ''"
        >
          <span class="nav-icon" v-html="item.icon"></span>
          <transition name="fade-x">
            <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          </transition>
          <transition name="fade-x">
            <span v-if="!collapsed && item.tag" class="nav-tag">{{ item.tag }}</span>
          </transition>
        </router-link>

        <template v-if="auth.isAdmin">
          <div class="nav-section-label" v-if="!collapsed" style="margin-top:8px">系统管理</div>
          <div class="nav-divider" v-if="collapsed"></div>
          <router-link
            to="/users"
            class="nav-item"
            :class="{ active: $route.path === '/users' }"
            :title="collapsed ? '用户管理' : ''"
          >
            <span class="nav-icon" v-html="icons.users"></span>
            <transition name="fade-x">
              <span v-if="!collapsed" class="nav-label">用户管理</span>
            </transition>
          </router-link>
        </template>
      </nav>

      <!-- 折叠按钮 -->
      <div class="sidebar-collapse" @click="collapsed = !collapsed" :title="collapsed ? '展开' : '收起'">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path v-if="!collapsed" d="M15 18l-6-6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path v-else d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <transition name="fade-x">
          <span v-if="!collapsed">{{ lang.t('收起侧栏') }}</span>
        </transition>
      </div>
    </aside>

    <!-- 右侧主区域 -->
    <div class="main-wrap">
      <!-- 顶栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <nav class="breadcrumb">
            <span class="bc-home">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke="#94a3b8" stroke-width="1.8"/>
                <polyline points="9 22 9 12 15 12 15 22" stroke="#94a3b8" stroke-width="1.8"/>
              </svg>
            </span>
            <span class="bc-sep">/</span>
            <span class="bc-cur">{{ $route.meta.title || 'AutoOps' }}</span>
          </nav>
        </div>
        <div class="topbar-right">
          <div class="lang-switch" @click="lang.toggle()" :title="lang.isZh ? 'Switch to English' : '切换中文'">
            <span class="lang-opt" :class="{ active: lang.isZh }">中</span>
            <span class="lang-sep">/</span>
            <span class="lang-opt" :class="{ active: !lang.isZh }">EN</span>
          </div>
          <div class="topbar-badge" :class="auth.role">
            <span class="badge-dot"></span>
            {{ lang.t(auth.role) }}
          </div>
          <el-dropdown @command="handleCommand" trigger="click">
            <div class="user-pill">
              <div class="user-avatar">{{ auth.username?.charAt(0)?.toUpperCase() }}</div>
              <span class="user-name">{{ auth.username }}</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                <path d="M6 9l6 6 6-6" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="margin-right:6px;vertical-align:middle">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" stroke="#606266" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  {{ lang.t('退出登录') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="page-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useLangStore } from '@/stores/lang'

const auth = useAuthStore()
const lang = useLangStore()
const collapsed = ref(false)

const roleLabel = computed(() => lang.t(auth.role))

const icons = {
  dashboard: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.8"/><rect x="14" y="3" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.8"/><rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.8"/><rect x="14" y="14" width="7" height="7" rx="1.5" stroke="currentColor" stroke-width="1.8"/></svg>`,
  servers: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none"><rect x="2" y="2" width="20" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/><rect x="2" y="14" width="20" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/><circle cx="6" cy="6" r="1.2" fill="currentColor"/><circle cx="6" cy="18" r="1.2" fill="currentColor"/><line x1="10" y1="6" x2="18" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="10" y1="18" x2="18" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  apps: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  containers: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" stroke="currentColor" stroke-width="1.8"/><polyline points="3.27 6.96 12 12.01 20.73 6.96" stroke="currentColor" stroke-width="1.8"/><line x1="12" y1="22.08" x2="12" y2="12" stroke="currentColor" stroke-width="1.8"/></svg>`,
  deploy: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  monitor: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  logs: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" stroke-width="1.8"/><polyline points="14 2 14 8 20 8" stroke="currentColor" stroke-width="1.8"/><line x1="16" y1="13" x2="8" y2="13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="16" y1="17" x2="8" y2="17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`,
  tasks: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="1.8"/><path d="M9 12l2 2 4-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  users: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="9" cy="7" r="4" stroke="currentColor" stroke-width="1.8"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`,
}

const mainMenu = [
  { path: '/dashboard', label: lang.t('仪表盘'), icon: icons.dashboard },
  { path: '/servers',   label: lang.t('服务器管理'), icon: icons.servers },
  { path: '/apps',      label: lang.t('应用管理'), icon: icons.apps },
  { path: '/containers',label: lang.t('容器管理'), icon: icons.containers },
  { path: '/deploy',    label: lang.t('CI/CD 部署'), icon: icons.deploy },
  { path: '/monitor',   label: lang.t('监控告警'), icon: icons.monitor },
  { path: '/logs',      label: lang.t('日志查询'), icon: icons.logs },
  { path: '/tasks',     label: lang.t('Ansible 任务'), icon: icons.tasks },
]

function handleCommand(cmd) {
  if (cmd === 'logout') auth.logout()
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  background: #f1f5f9;
  overflow: hidden;
}

/* ── 侧边栏 ── */
.sidebar {
  width: 224px;
  min-width: 224px;
  background: #fff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  transition: width 0.22s ease, min-width 0.22s ease;
  overflow: hidden;
  z-index: 20;
}
.sidebar.collapsed {
  width: 64px;
  min-width: 64px;
}

/* Logo */
.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 18px;
  gap: 10px;
  border-bottom: 1px solid #f1f5f9;
  flex-shrink: 0;
}
.logo-icon { flex-shrink: 0; display: flex; }
.logo-text {
  font-size: 17px;
  font-weight: 800;
  color: #1e40af;
  letter-spacing: 1px;
  white-space: nowrap;
}

/* 导航 */
.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  overflow-y: auto;
  overflow-x: hidden;
}
.sidebar-nav::-webkit-scrollbar { width: 0; }

.nav-section-label {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  padding: 8px 8px 4px;
  white-space: nowrap;
}
.nav-divider {
  height: 1px;
  background: #f1f5f9;
  margin: 8px 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 8px;
  color: #64748b;
  text-decoration: none;
  transition: all 0.15s;
  margin-bottom: 1px;
  white-space: nowrap;
  position: relative;
}
.nav-item:hover {
  background: #eff6ff;
  color: #2563eb;
}
.nav-item.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 3px;
  background: #3b82f6;
  border-radius: 0 3px 3px 0;
}

.nav-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.nav-label {
  font-size: 13.5px;
  white-space: nowrap;
  flex: 1;
}
.nav-tag {
  font-size: 10px;
  background: #dbeafe;
  color: #2563eb;
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 600;
}

/* 折叠按钮 */
.sidebar-collapse {
  height: 48px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 18px;
  border-top: 1px solid #f1f5f9;
  color: #94a3b8;
  cursor: pointer;
  font-size: 13px;
  transition: color 0.15s;
  flex-shrink: 0;
  white-space: nowrap;
}
.sidebar-collapse:hover { color: #3b82f6; }

/* ── 主区域 ── */
.main-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* 顶栏 */
.topbar {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
}
.bc-home { display: flex; align-items: center; }
.bc-sep { color: #cbd5e1; font-size: 14px; }
.bc-cur { font-size: 14px; font-weight: 600; color: #0f172a; }

.topbar-right { display: flex; align-items: center; gap: 12px; }

.topbar-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
}
.topbar-badge.admin { background: #fef2f2; color: #ef4444; }
.topbar-badge.operator { background: #fffbeb; color: #f59e0b; }
.topbar-badge.viewer { background: #f0fdf4; color: #22c55e; }
.badge-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px 5px 5px;
  border-radius: 24px;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.user-pill:hover {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.08);
}
.user-avatar {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: white;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.user-name { font-size: 13px; font-weight: 500; color: #374151; }

/* 内容区 */
.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}
.page-content::-webkit-scrollbar { width: 6px; }
.page-content::-webkit-scrollbar-track { background: transparent; }
.page-content::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }

/* 过渡 */
.fade-x-enter-active, .fade-x-leave-active { transition: opacity 0.15s, transform 0.15s; }
.fade-x-enter-from, .fade-x-leave-to { opacity: 0; transform: translateX(-6px); }
</style>
