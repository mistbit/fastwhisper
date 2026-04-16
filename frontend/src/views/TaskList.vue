<template>
  <div class="task-list-page">
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('taskListTitle') }}</h1>
        <p class="page-subtitle">{{ t('taskListSubtitle') }}</p>
      </div>
      <router-link to="/tasks/new" class="btn-primary">
        <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        {{ t('navNewTask') }}
      </router-link>
    </div>

    <!-- Filter chips -->
    <div class="filter-bar">
      <button
        v-for="filter in filters"
        :key="filter.value"
        class="filter-chip"
        :class="{ 'filter-chip-active': currentFilter === filter.value }"
        @click="applyFilter(filter.value)"
      >
        {{ filter.label }}
        <span v-if="filter.count !== undefined" class="filter-count">{{ filter.count }}</span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading && tasks.length === 0" class="loading-state">
      <div class="loader"></div>
    </div>

    <!-- Empty state -->
    <div v-else-if="tasks.length === 0" class="empty-state card">
      <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
      </svg>
      <p class="empty-title">{{ t('emptyTitle') }}</p>
      <p class="empty-body">{{ t('emptyBody') }}</p>
    </div>

    <!-- Task table -->
    <div v-else class="card">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>{{ t('colFilename') }}</th>
              <th>{{ t('colStatus') }}</th>
              <th>{{ t('colStage') }}</th>
              <th>{{ t('colCreated') }}</th>
              <th>{{ t('colDuration') }}</th>
              <th>{{ t('colActions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.task_id">
              <td>
                <router-link
                  :to="{ name: 'task-detail', params: { id: task.task_id } }"
                  class="filename-link"
                >
                  {{ task.filename }}
                </router-link>
              </td>
              <td>
                <span class="status-badge" :class="`status-badge-${task.status}`">
                  {{ getStatusText(task.status) }}
                </span>
              </td>
              <td class="cell-muted">{{ task.stage ? getStageText(task.stage) : '--' }}</td>
              <td class="cell-muted">{{ formatDate(task.created_at) }}</td>
              <td class="cell-muted">{{ getTimingText(task) }}</td>
              <td>
                <div class="action-group">
                  <router-link
                    :to="{ name: 'task-detail', params: { id: task.task_id } }"
                    class="action-btn"
                    :title="t('openTask')"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </router-link>
                  <button
                    v-if="task.status === 'failed'"
                    class="action-btn action-btn-retry"
                    :disabled="retryingId === task.task_id"
                    :title="t('retry')"
                    @click="handleRetry(task)"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
                    </svg>
                  </button>
                  <button
                    class="action-btn action-btn-delete"
                    :title="t('delete')"
                    @click="handleDelete(task)"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="pagination">
        <span class="pagination-info">{{ t('pageTotal', { count: total }) }}</span>
        <div class="pagination-controls">
          <button
            class="pagination-btn"
            :disabled="page <= 1"
            @click="goPage(page - 1)"
          >
            {{ t('paginationPrev') }}
          </button>
          <span class="pagination-current">{{ page }}</span>
          <button
            class="pagination-btn"
            :disabled="!hasMore"
            @click="goPage(page + 1)"
          >
            {{ t('paginationNext') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useTaskStore } from '../stores/task'
import { useLocale } from '../composables/useLocale'

const taskStore = useTaskStore()
const { locale, t } = useLocale()

const retryingId = ref('')
const refreshInterval = ref(null)

const tasks = computed(() => taskStore.tasks)
const loading = computed(() => taskStore.loading)
const total = computed(() => taskStore.total)
const page = computed(() => taskStore.page)
const hasMore = computed(() => taskStore.hasMore)
const currentFilter = computed(() => taskStore.statusFilter)
const stats = computed(() => taskStore.stats)

const filters = computed(() => [
  { value: '', label: t('filterAll'), count: stats.value.total },
  { value: 'pending', label: t('filterPending'), count: stats.value.pending },
  { value: 'processing', label: t('filterProcessing'), count: stats.value.processing },
  { value: 'completed', label: t('filterCompleted'), count: stats.value.completed },
  { value: 'failed', label: t('filterFailed'), count: stats.value.failed },
])

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
  refreshInterval.value = window.setInterval(() => {
    const hasActive = taskStore.tasks.some((task) =>
      ['pending', 'processing'].includes(task.status)
    )
    if (hasActive) {
      taskStore.fetchTasks({ page: taskStore.page })
      taskStore.fetchOverview()
    }
  }, 5000)
}

function applyFilter(status) {
  taskStore.fetchTasks({ page: 1, status })
}

function goPage(newPage) {
  taskStore.fetchTasks({ page: newPage })
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

function getTimingText(task) {
  if (task.processing_seconds) {
    return t('processingMetric', { value: formatDuration(task.processing_seconds) })
  }
  if (task.queue_seconds) {
    return t('queueMetric', { value: formatDuration(task.queue_seconds) })
  }
  return '--'
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

function formatDuration(seconds) {
  if (seconds == null) return '--'
  const rounded = Math.max(0, Math.round(seconds))
  if (rounded < 60) return locale.value === 'zh' ? `${rounded} 秒` : `${rounded}s`
  const minutes = Math.floor(rounded / 60)
  const remainSeconds = rounded % 60
  if (minutes < 60) {
    return locale.value === 'zh'
      ? (remainSeconds ? `${minutes} 分 ${remainSeconds} 秒` : `${minutes} 分`)
      : (remainSeconds ? `${minutes}m ${remainSeconds}s` : `${minutes}m`)
  }
  const hours = Math.floor(minutes / 60)
  const remainMinutes = minutes % 60
  return locale.value === 'zh'
    ? (remainMinutes ? `${hours} 时 ${remainMinutes} 分` : `${hours} 时`)
    : (remainMinutes ? `${hours}h ${remainMinutes}m` : `${hours}h`)
}

async function handleRetry(task) {
  retryingId.value = task.task_id
  try {
    await taskStore.retryTask(task.task_id)
    await taskStore.fetchTasks({ page: taskStore.page })
  } finally {
    retryingId.value = ''
  }
}

async function handleDelete(task) {
  const confirmed = window.confirm(t('confirmDelete', { filename: task.filename }))
  if (!confirmed) return
  await taskStore.deleteTask(task.task_id)
  await taskStore.fetchTasks({ page: 1 })
}
</script>

<style scoped>
.task-list-page {
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

/* ── Filter bar ── */
.filter-bar {
  @apply flex flex-wrap gap-2;
}

.filter-chip {
  @apply inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium transition-colors duration-150;
  border-color: var(--line);
  background: white;
  color: var(--muted);
}

.filter-chip:hover {
  border-color: rgba(0, 113, 227, 0.2);
  color: var(--text-strong);
}

.filter-chip-active {
  border-color: var(--accent);
  background: rgba(0, 113, 227, 0.06);
  color: var(--accent);
}

.filter-count {
  @apply rounded-full px-1.5 py-0.5 text-xs;
  background: rgba(0, 0, 0, 0.05);
}

.filter-chip-active .filter-count {
  background: rgba(0, 113, 227, 0.12);
  color: var(--accent);
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

.filename-link {
  @apply block max-w-[280px] truncate font-medium transition-colors duration-150;
  color: var(--text-strong);
}

.filename-link:hover {
  color: var(--accent);
}

.cell-muted {
  color: var(--muted);
}

/* ── Actions ── */
.action-group {
  @apply flex items-center gap-1;
}

.action-btn {
  @apply inline-flex items-center justify-center rounded-md p-1.5 transition-colors duration-150;
  color: var(--muted);
}

.action-btn:hover {
  background: var(--surface-alt);
  color: var(--accent);
}

.action-btn-retry:hover {
  color: var(--warning);
}

.action-btn-delete:hover {
  color: var(--danger);
}

.action-btn:disabled {
  @apply cursor-not-allowed opacity-40;
}

/* ── Pagination ── */
.pagination {
  @apply flex items-center justify-between border-t px-4 py-3;
  border-color: var(--line);
}

.pagination-info {
  @apply text-sm;
  color: var(--muted);
}

.pagination-controls {
  @apply flex items-center gap-2;
}

.pagination-btn {
  @apply rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors duration-150;
  border-color: var(--line);
  color: var(--text-strong);
}

.pagination-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.pagination-btn:disabled {
  @apply cursor-not-allowed opacity-40;
}

.pagination-current {
  @apply min-w-[2rem] text-center text-sm font-medium;
  color: var(--text-strong);
}

/* ── States ── */
.loading-state {
  @apply flex min-h-[200px] items-center justify-center;
}

.loader {
  @apply h-8 w-8 animate-spin rounded-full border-2 border-t-transparent;
  border-color: var(--accent);
  border-top-color: transparent;
}

.empty-state {
  @apply flex min-h-[240px] flex-col items-center justify-center gap-3 p-6 text-center;
}

.empty-icon {
  @apply h-12 w-12;
  color: var(--muted);
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
