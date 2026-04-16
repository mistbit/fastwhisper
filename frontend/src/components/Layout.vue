<template>
  <div class="shell" :class="{ 'shell-collapsed': collapsed }">
    <!-- Mobile overlay -->
    <div
      v-if="mobileOpen"
      class="mobile-backdrop"
      @click="mobileOpen = false"
    ></div>

    <!-- Sidebar -->
    <aside
      class="sidebar"
      :class="{ 'sidebar-mobile-open': mobileOpen }"
    >
      <!-- Brand -->
      <div class="sidebar-brand">
        <router-link to="/" class="brand-link" @click="mobileOpen = false">
          <span class="brand-mark">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
            </svg>
          </span>
          <transition name="fade">
            <div v-if="!collapsed" class="brand-text">
              <p class="brand-name">{{ t('brand') }}</p>
              <p class="brand-sub">{{ t('productName') }}</p>
            </div>
          </transition>
        </router-link>
      </div>

      <!-- Navigation -->
      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ 'nav-item-active': isNavActive(item) }"
          :title="collapsed ? item.label : ''"
          @click="mobileOpen = false"
        >
          <span class="nav-icon" v-html="item.icon"></span>
          <transition name="fade">
            <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          </transition>
        </router-link>
      </nav>

      <!-- Bottom -->
      <div class="sidebar-bottom">
        <div class="sidebar-bottom-row">
          <span class="runtime-pill">
            <span class="runtime-dot"></span>
            <transition name="fade">
              <span v-if="!collapsed">{{ t('navStatus') }}</span>
            </transition>
          </span>

          <button class="sidebar-btn" @click="toggleLocale" :title="t('languageSwitch')">
            {{ t('languageSwitch') }}
          </button>
        </div>

        <button class="collapse-btn" @click="collapsed = !collapsed">
          <svg
            class="collapse-icon"
            :class="{ 'collapse-icon-flipped': collapsed }"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
          <transition name="fade">
            <span v-if="!collapsed" class="collapse-label">
              {{ collapsed ? t('navExpand') : t('navCollapse') }}
            </span>
          </transition>
        </button>
      </div>
    </aside>

    <!-- Main -->
    <div class="main-wrapper">
      <!-- Top bar -->
      <header class="topbar">
        <div class="topbar-left">
          <button class="mobile-menu-btn" @click="mobileOpen = !mobileOpen">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>

          <nav class="breadcrumb">
            <template v-for="(crumb, index) in breadcrumbs" :key="crumb.path">
              <span v-if="index > 0" class="breadcrumb-sep">/</span>
              <router-link
                v-if="index < breadcrumbs.length - 1"
                :to="crumb.path"
                class="breadcrumb-link"
              >
                {{ crumb.label }}
              </router-link>
              <span v-else class="breadcrumb-current">{{ crumb.label }}</span>
            </template>
          </nav>
        </div>
      </header>

      <!-- Content -->
      <main class="main-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useLocale } from '../composables/useLocale'

const route = useRoute()
const { t, toggleLocale } = useLocale()

const collapsed = ref(false)
const mobileOpen = ref(false)

const navItems = computed(() => [
  {
    to: '/',
    label: t('navDashboard'),
    routeName: 'dashboard',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" /></svg>',
  },
  {
    to: '/tasks',
    label: t('navTasks'),
    routeName: 'task-list',
    matchPrefix: '/tasks',
    excludeExact: ['/tasks/new'],
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 6.75h12M8.25 12h12M8.25 17.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" /></svg>',
  },
  {
    to: '/tasks/new',
    label: t('navNewTask'),
    routeName: 'new-task',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>',
  },
])

function isNavActive(item) {
  if (route.name === item.routeName) return true
  if (item.matchPrefix && route.path.startsWith(item.matchPrefix)) {
    if (item.excludeExact && item.excludeExact.includes(route.path)) return false
    return true
  }
  return false
}

const breadcrumbs = computed(() => {
  const crumbs = [{ path: '/', label: t('breadDashboard') }]

  if (route.name === 'task-list') {
    crumbs.push({ path: '/tasks', label: t('breadTasks') })
  } else if (route.name === 'new-task') {
    crumbs.push({ path: '/tasks', label: t('breadTasks') })
    crumbs.push({ path: '/tasks/new', label: t('breadNewTask') })
  } else if (route.name === 'task-detail') {
    crumbs.push({ path: '/tasks', label: t('breadTasks') })
    crumbs.push({ path: route.path, label: t('breadDetail') })
  }

  return crumbs
})
</script>

<style scoped>
.shell {
  @apply flex min-h-screen;
}

/* ── Sidebar ── */
.sidebar {
  @apply fixed left-0 top-0 z-40 flex h-screen flex-col;
  width: var(--sidebar-width);
  background: var(--sidebar-bg);
  border-right: 1px solid var(--sidebar-border);
  transition: width 0.2s ease;
}

.shell-collapsed .sidebar {
  width: var(--sidebar-width-collapsed);
}

.sidebar-brand {
  @apply flex items-center px-4 py-5;
  border-bottom: 1px solid var(--sidebar-border);
}

.brand-link {
  @apply flex items-center gap-3;
}

.brand-mark {
  @apply flex h-9 w-9 shrink-0 items-center justify-center rounded-lg;
  background: rgba(0, 113, 227, 0.2);
  color: #60a5fa;
}

.brand-text {
  @apply min-w-0;
}

.brand-name {
  @apply text-sm font-semibold;
  color: var(--sidebar-text-active);
}

.brand-sub {
  @apply text-xs;
  color: var(--sidebar-text);
}

/* ── Nav ── */
.sidebar-nav {
  @apply flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-4;
}

.nav-item {
  @apply flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150;
  color: var(--sidebar-text);
}

.nav-item:hover {
  background: var(--sidebar-bg-hover);
  color: var(--sidebar-text-hover);
}

.nav-item-active {
  background: var(--sidebar-bg-active);
  color: var(--sidebar-text-active);
}

.nav-icon {
  @apply flex h-5 w-5 shrink-0 items-center justify-center;
}

.nav-icon :deep(svg) {
  @apply h-5 w-5;
}

.nav-label {
  @apply truncate;
}

/* ── Sidebar bottom ── */
.sidebar-bottom {
  @apply space-y-2 px-3 py-4;
  border-top: 1px solid var(--sidebar-border);
}

.sidebar-bottom-row {
  @apply flex items-center gap-2 px-1;
}

.runtime-pill {
  @apply inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs;
  background: rgba(255, 255, 255, 0.06);
  color: var(--sidebar-text);
}

.runtime-dot {
  @apply h-1.5 w-1.5 shrink-0 rounded-full;
  background: #22c55e;
}

.sidebar-btn {
  @apply inline-flex items-center justify-center rounded-md px-2 py-1 text-xs font-medium transition-colors duration-150;
  color: var(--sidebar-text);
  background: rgba(255, 255, 255, 0.06);
}

.sidebar-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: var(--sidebar-text-hover);
}

.collapse-btn {
  @apply flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors duration-150;
  color: var(--sidebar-text);
}

.collapse-btn:hover {
  background: var(--sidebar-bg-hover);
  color: var(--sidebar-text-hover);
}

.collapse-icon {
  @apply h-4 w-4 shrink-0 transition-transform duration-200;
}

.collapse-icon-flipped {
  transform: rotate(180deg);
}

.collapse-label {
  @apply truncate;
}

/* ── Main wrapper ── */
.main-wrapper {
  @apply flex min-h-screen min-w-0 flex-1 flex-col;
  margin-left: var(--sidebar-width);
  transition: margin-left 0.2s ease;
}

.shell-collapsed .main-wrapper {
  margin-left: var(--sidebar-width-collapsed);
}

/* ── Top bar ── */
.topbar {
  @apply sticky top-0 z-20 flex items-center justify-between border-b px-6 py-3;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-color: var(--line);
}

.topbar-left {
  @apply flex items-center gap-3;
}

.mobile-menu-btn {
  @apply hidden items-center justify-center rounded-lg p-1.5 transition-colors;
  color: var(--muted);
}

.mobile-menu-btn:hover {
  background: var(--surface-alt);
  color: var(--text-strong);
}

.breadcrumb {
  @apply flex items-center gap-1.5 text-sm;
}

.breadcrumb-sep {
  color: var(--line-strong);
}

.breadcrumb-link {
  @apply transition-colors duration-150;
  color: var(--muted);
}

.breadcrumb-link:hover {
  color: var(--accent);
}

.breadcrumb-current {
  @apply font-medium;
  color: var(--text-strong);
}

/* ── Content ── */
.main-content {
  @apply flex-1 px-6 py-6;
}

/* ── Transitions ── */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ── Mobile ── */
.mobile-backdrop {
  @apply fixed inset-0 z-30;
  background: rgba(0, 0, 0, 0.5);
}

@media (max-width: 1023px) {
  .sidebar {
    @apply -translate-x-full;
    width: var(--sidebar-width) !important;
  }

  .sidebar-mobile-open {
    @apply translate-x-0;
  }

  .shell-collapsed .sidebar {
    width: var(--sidebar-width) !important;
  }

  .main-wrapper {
    margin-left: 0 !important;
  }

  .mobile-menu-btn {
    @apply flex;
  }

  .collapse-btn {
    @apply hidden;
  }
}
</style>
