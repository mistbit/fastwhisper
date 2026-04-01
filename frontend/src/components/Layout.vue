<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="sidebar-top">
        <div class="brand-row">
          <router-link to="/" class="brand">
            <span class="brand-mark"></span>
            <div class="brand-copy">
              <p class="brand-name">{{ t('brand') }}</p>
              <p class="brand-product">{{ t('productName') }}</p>
            </div>
          </router-link>

          <div class="sidebar-tools">
            <span class="runtime-pill">
              <span class="runtime-dot"></span>
              {{ t('navStatus') }}
            </span>

            <button class="locale-button" @click="toggleLocale">
              {{ t('languageSwitch') }}
            </button>
          </div>
        </div>

        <p class="sidebar-description">{{ t('productTagline') }}</p>
      </div>

      <nav class="sidebar-nav">
        <router-link
          to="/"
          class="nav-link"
          :class="{ 'nav-link-active': route.name === 'home' }"
        >
          {{ t('navHome') }}
        </router-link>
      </nav>

      <div class="sidebar-history">
        <div class="sidebar-history-head">
          <span class="sidebar-history-title">{{ t('queueTitle') }}</span>
          <span class="sidebar-history-count">{{ total }}</span>
        </div>

        <div v-if="sidebarLoading && sidebarTasks.length === 0" class="sidebar-empty">
          {{ t('emptyTitle') }}
        </div>

        <div v-else-if="sidebarTasks.length === 0" class="sidebar-empty">
          {{ t('emptyBody') }}
        </div>

        <div v-else class="sidebar-history-list">
          <button
            v-for="task in sidebarTasks"
            :key="task.task_id"
            class="sidebar-task"
            :class="{ 'sidebar-task-active': activeTaskId === task.task_id }"
            @click="openTask(task)"
          >
            <span class="sidebar-task-dot" :class="`sidebar-task-dot-${task.status}`"></span>

            <div class="sidebar-task-copy">
              <p class="sidebar-task-name">{{ task.filename }}</p>
              <p class="sidebar-task-meta">
                {{ task.stage ? getStageText(task.stage) : getStatusText(task.status) }}
              </p>
            </div>
          </button>
        </div>
      </div>
    </aside>

    <main class="main">
      <div class="main-inner">
        <section class="main-content">
          <slot />
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTaskStore } from '../stores/task'
import { useLocale } from '../composables/useLocale'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()
const { t, toggleLocale } = useLocale()

const sidebarTasks = computed(() => taskStore.tasks.slice(0, 10))
const sidebarLoading = computed(() => taskStore.loading)
const total = computed(() => taskStore.total)
const activeTaskId = computed(() => {
  if (route.name === 'task-detail') {
    return String(route.params.id || '')
  }
  return taskStore.currentTask?.task_id || ''
})

onMounted(() => {
  if (taskStore.tasks.length === 0) {
    taskStore.fetchTasks({ page: 1 })
  }
})

watch(() => route.name, (name) => {
  if (name === 'task-detail' && taskStore.tasks.length === 0) {
    taskStore.fetchTasks({ page: 1 })
  }
})

function openTask(task) {
  taskStore.setCurrentTask(task)
  router.push({ name: 'task-detail', params: { id: task.task_id } })
}

function getStatusText(status) {
  return {
    pending: t('pendingBadge'),
    processing: t('processingBadge'),
    completed: t('completedBadge'),
    failed: t('failedBadge'),
  }[status] || status
}

function getStageText(stage) {
  return {
    queued: t('stageQueued'),
    preprocessing: t('stagePreprocessing'),
    transcribing: t('stageTranscribing'),
    diarizing: t('stageDiarizing'),
    generating: t('stageGenerating'),
    saving: t('stageSaving'),
    failed: t('stageFailed'),
  }[stage] || stage
}
</script>

<style scoped>
.shell {
  @apply min-h-screen lg:grid lg:grid-cols-[320px_1fr];
  background: var(--bg-canvas);
}

.sidebar {
  @apply flex flex-col gap-8 border-b border-[var(--line)] px-5 py-5 lg:sticky lg:top-0 lg:h-screen lg:self-start lg:border-b-0 lg:border-r lg:px-6 lg:py-6;
  background: var(--sidebar-bg);
}

.sidebar-top {
  @apply space-y-5;
}

.brand-row {
  @apply flex items-start justify-between gap-3;
}

.brand {
  @apply flex items-center gap-3;
}

.brand-mark {
  @apply inline-flex h-9 w-9 rounded-full;
  background: linear-gradient(135deg, var(--accent), #7db7ff);
  box-shadow: inset 0 0 0 9px rgba(255, 255, 255, 0.92);
}

.brand-copy {
  @apply min-w-0;
}

.brand-name {
  @apply text-sm font-medium text-[var(--text-strong)];
}

.brand-product {
  @apply text-sm text-[var(--muted)];
}

.sidebar-description {
  @apply max-w-[13rem] text-sm leading-6 text-[var(--muted)];
}

.sidebar-nav {
  @apply space-y-1;
}

.sidebar-history {
  @apply min-h-0 flex-1 space-y-3;
}

.sidebar-history-head {
  @apply flex items-center justify-between gap-3 px-1;
}

.sidebar-history-title {
  @apply text-xs font-medium uppercase tracking-[0.08em] text-[var(--muted)];
  font-family: var(--font-mono);
}

.sidebar-history-count {
  @apply text-xs text-[var(--muted)];
  font-family: var(--font-mono);
}

.sidebar-history-list {
  @apply flex max-h-[calc(100vh-18rem)] flex-col gap-2 overflow-auto pr-1;
}

.sidebar-task {
  @apply flex w-full items-start gap-3 rounded-2xl border px-3 py-3 text-left transition-colors duration-200;
  border-color: transparent;
  background: rgba(255, 255, 255, 0.58);
}

.sidebar-task:hover {
  border-color: rgba(0, 113, 227, 0.12);
  background: rgba(255, 255, 255, 0.9);
}

.sidebar-task-active {
  border-color: rgba(0, 113, 227, 0.18);
  background: rgba(0, 113, 227, 0.08);
}

.sidebar-task-dot {
  @apply mt-1.5 h-2 w-2 shrink-0 rounded-full;
}

.sidebar-task-dot-pending {
  background: #94a3b8;
}

.sidebar-task-dot-processing {
  background: var(--accent);
}

.sidebar-task-dot-completed {
  background: var(--success);
}

.sidebar-task-dot-failed {
  background: var(--danger);
}

.sidebar-task-copy {
  @apply min-w-0 flex-1;
}

.sidebar-task-name {
  @apply truncate text-sm font-medium text-[var(--text-strong)];
}

.sidebar-task-meta {
  @apply mt-1 text-xs leading-5 text-[var(--muted)];
}

.sidebar-empty {
  @apply rounded-2xl border px-4 py-4 text-sm leading-6 text-[var(--muted)];
  border-color: var(--line);
  background: rgba(255, 255, 255, 0.52);
}

.nav-link {
  @apply flex items-center rounded-xl px-3 py-2.5 text-sm transition-colors duration-200;
  color: var(--muted);
}

.nav-link:hover {
  background: rgba(0, 113, 227, 0.06);
  color: var(--text-strong);
}

.nav-link-active {
  background: rgba(0, 113, 227, 0.1);
  color: var(--accent);
}

.sidebar-tools {
  @apply flex items-center gap-2 pt-1;
}

.runtime-pill,
.locale-button {
  @apply inline-flex items-center justify-center gap-1.5 rounded-full border px-2.5 py-1.5 text-xs;
  border-color: var(--line);
  background: rgba(255, 255, 255, 0.64);
  white-space: nowrap;
}

.runtime-pill {
  color: var(--text-strong);
}

.runtime-dot {
  @apply h-1.5 w-1.5 rounded-full;
  background: var(--success);
}

.locale-button {
  @apply transition-colors duration-200;
  color: var(--text-strong);
}

.locale-button:hover {
  background: white;
}

.main {
  @apply min-w-0;
}

.main-inner {
  @apply mx-auto max-w-[1360px] px-5 py-5 md:px-8 md:py-6 xl:px-10;
}

.main-content {
  @apply min-w-0;
}
</style>
