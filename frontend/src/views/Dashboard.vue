<template>
  <div class="dashboard">
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('dashTitle') }}</h1>
        <p class="page-subtitle">{{ t('dashSubtitle') }}</p>
      </div>
      <router-link to="/tasks/new" class="btn-primary">
        <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        {{ t('navNewTask') }}
      </router-link>
    </div>

    <!-- Stats cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon stat-icon-total">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-label">{{ t('statTotal') }}</span>
          <strong class="stat-value">{{ stats.total }}</strong>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-icon-pending">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-label">{{ t('statPending') }}</span>
          <strong class="stat-value">{{ stats.pending }}</strong>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-icon-processing">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-label">{{ t('statProcessing') }}</span>
          <strong class="stat-value">{{ stats.processing }}</strong>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-icon-completed">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-label">{{ t('statCompleted') }}</span>
          <strong class="stat-value">{{ stats.completed }}</strong>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-icon-failed">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-label">{{ t('statFailed') }}</span>
          <strong class="stat-value">{{ stats.failed }}</strong>
        </div>
      </div>
    </div>

    <!-- Active tasks -->
    <section v-if="activeTasks.length > 0" class="section">
      <h2 class="section-title">{{ t('dashActiveTitle') }}</h2>
      <div class="active-grid">
        <div v-for="task in activeTasks" :key="task.task_id" class="active-card card">
          <div class="active-card-top">
            <div class="active-card-info">
              <p class="active-card-name">{{ task.filename }}</p>
              <p class="active-card-meta">
                {{ task.stage ? getStageText(task.stage) : getStatusText(task.status) }}
              </p>
            </div>
            <span class="status-badge" :class="`status-badge-${task.status}`">
              {{ getStatusText(task.status) }}
            </span>
          </div>
          <div v-if="task.status === 'processing'" class="active-card-progress">
            <div class="progress-track">
              <div class="progress-bar" :style="{ width: `${task.progress || 0}%` }"></div>
            </div>
            <span class="progress-label">{{ task.progress || 0 }}%</span>
          </div>
          <router-link
            :to="{ name: 'task-detail', params: { id: task.task_id } }"
            class="active-card-link"
          >
            {{ t('openTask') }}
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
          </router-link>
        </div>
      </div>
    </section>

    <!-- Recent tasks -->
    <section class="section">
      <div class="section-header">
        <h2 class="section-title">{{ t('dashRecentTitle') }}</h2>
        <router-link to="/tasks" class="section-link">
          {{ t('navTasks') }}
          <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </router-link>
      </div>

      <div v-if="recentTasks.length === 0" class="empty-state card">
        <p class="empty-title">{{ t('dashRecentEmpty') }}</p>
        <p class="empty-body">{{ t('emptyBody') }}</p>
      </div>

      <div v-else class="card">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('colFilename') }}</th>
                <th>{{ t('colStatus') }}</th>
                <th>{{ t('colStage') }}</th>
                <th>{{ t('colCreated') }}</th>
                <th>{{ t('colActions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in recentTasks" :key="task.task_id">
                <td class="cell-filename">{{ task.filename }}</td>
                <td>
                  <span class="status-badge" :class="`status-badge-${task.status}`">
                    {{ getStatusText(task.status) }}
                  </span>
                </td>
                <td class="cell-muted">{{ task.stage ? getStageText(task.stage) : '--' }}</td>
                <td class="cell-muted">{{ formatDate(task.created_at) }}</td>
                <td>
                  <router-link
                    :to="{ name: 'task-detail', params: { id: task.task_id } }"
                    class="table-link"
                  >
                    {{ t('openTask') }}
                  </router-link>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useTaskStore } from '../stores/task'
import { useLocale } from '../composables/useLocale'

const taskStore = useTaskStore()
const { locale, t } = useLocale()

const refreshInterval = ref(null)
const stats = computed(() => taskStore.stats)
const recentTasks = computed(() => taskStore.tasks.slice(0, 8))
const activeTasks = computed(() =>
  taskStore.tasks.filter((task) => ['pending', 'processing'].includes(task.status))
)

onMounted(async () => {
  await Promise.all([
    taskStore.fetchOverview(),
    taskStore.fetchTasks({ page: 1 }),
  ])
  startRefreshLoop()
})

onUnmounted(() => {
  if (refreshInterval.value) {
    window.clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
})

function startRefreshLoop() {
  refreshInterval.value = window.setInterval(async () => {
    const hasActive = taskStore.tasks.some((task) =>
      ['pending', 'processing'].includes(task.status)
    )
    if (hasActive) {
      await Promise.all([
        taskStore.fetchOverview(),
        taskStore.fetchTasks({ page: 1 }),
      ])
    }
  }, 5000)
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

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString(locale.value === 'zh' ? 'zh-CN' : 'en-US', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.dashboard {
  @apply space-y-6;
}

/* ── Page header ── */
.page-header {
  @apply flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between;
}

.page-title {
  @apply text-2xl font-semibold tracking-tight;
  color: var(--text-strong);
}

.page-subtitle {
  @apply mt-1 text-sm;
  color: var(--muted);
}

/* ── Stats grid ── */
.stats-grid {
  @apply grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5;
}

.stat-card {
  @apply flex items-center gap-4 rounded-xl border bg-white px-5 py-4;
  border-color: var(--line);
  box-shadow: var(--shadow-card);
}

.stat-icon {
  @apply flex h-10 w-10 shrink-0 items-center justify-center rounded-lg;
}

.stat-icon-total {
  background: rgba(100, 116, 139, 0.1);
  color: #64748b;
}

.stat-icon-pending {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning);
}

.stat-icon-processing {
  background: rgba(0, 113, 227, 0.1);
  color: var(--accent);
}

.stat-icon-completed {
  background: rgba(10, 127, 85, 0.1);
  color: var(--success);
}

.stat-icon-failed {
  background: rgba(255, 59, 48, 0.1);
  color: var(--danger);
}

.stat-content {
  @apply min-w-0;
}

.stat-label {
  @apply text-xs font-medium uppercase tracking-wider;
  color: var(--muted);
}

.stat-value {
  @apply mt-0.5 block text-2xl font-semibold tracking-tight;
  color: var(--text-strong);
}

/* ── Sections ── */
.section {
  @apply space-y-4;
}

.section-header {
  @apply flex items-center justify-between;
}

.section-title {
  @apply text-base font-semibold;
  color: var(--text-strong);
}

.section-link {
  @apply flex items-center gap-1 text-sm font-medium transition-colors duration-150;
  color: var(--accent);
}

.section-link:hover {
  color: var(--accent-strong);
}

/* ── Active cards ── */
.active-grid {
  @apply grid gap-4 sm:grid-cols-2 lg:grid-cols-3;
}

.active-card {
  @apply flex flex-col gap-3 p-4;
}

.active-card-top {
  @apply flex items-start justify-between gap-3;
}

.active-card-info {
  @apply min-w-0 flex-1;
}

.active-card-name {
  @apply truncate text-sm font-medium;
  color: var(--text-strong);
}

.active-card-meta {
  @apply mt-1 text-xs;
  color: var(--muted);
}

.active-card-progress {
  @apply flex items-center gap-3;
}

.progress-track {
  @apply h-1.5 flex-1 overflow-hidden rounded-full;
  background: rgba(0, 113, 227, 0.1);
}

.progress-bar {
  @apply h-full rounded-full transition-all duration-500;
  background: var(--accent);
}

.progress-label {
  @apply text-xs font-medium;
  color: var(--accent);
}

.active-card-link {
  @apply flex items-center gap-1 text-xs font-medium transition-colors duration-150;
  color: var(--accent);
}

.active-card-link:hover {
  color: var(--accent-strong);
}

/* ── Table ── */
.table-wrapper {
  @apply overflow-x-auto;
}

.data-table {
  @apply w-full text-sm;
}

.data-table th {
  @apply border-b px-4 py-3 text-left text-xs font-medium uppercase tracking-wider;
  border-color: var(--line);
  color: var(--muted);
  background: var(--surface-alt);
}

.data-table td {
  @apply border-b px-4 py-3;
  border-color: var(--line-soft);
  color: var(--text-strong);
}

.data-table tbody tr:last-child td {
  @apply border-b-0;
}

.data-table tbody tr {
  @apply transition-colors duration-100;
}

.data-table tbody tr:hover {
  background: rgba(0, 113, 227, 0.02);
}

.cell-filename {
  @apply max-w-[240px] truncate font-medium;
}

.cell-muted {
  color: var(--muted);
}

.table-link {
  @apply text-sm font-medium transition-colors duration-150;
  color: var(--accent);
}

.table-link:hover {
  color: var(--accent-strong);
}

/* ── Empty state ── */
.empty-state {
  @apply flex min-h-[160px] flex-col items-center justify-center gap-2 p-6 text-center;
}

.empty-title {
  @apply text-sm font-medium;
  color: var(--text-strong);
}

.empty-body {
  @apply text-sm;
  color: var(--muted);
}
</style>
