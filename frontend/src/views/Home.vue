<template>
  <div class="home-page">
    <section class="surface upload-surface">
      <div class="surface-head">
        <div>
          <p class="eyebrow">{{ t('workspaceTitle') }}</p>
          <h1 class="hero-title">{{ t('uploadPanelTitle') }}</h1>
          <p class="surface-copy">{{ t('workspaceBody') }}</p>
        </div>
      </div>

      <div class="upload-grid">
        <div
          class="dropzone"
          :class="{ 'dropzone-active': isDragging, 'dropzone-disabled': uploading }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
          @click="!uploading && fileInput?.click()"
        >
          <input
            ref="fileInput"
            type="file"
            :accept="acceptTypes"
            class="hidden"
            @change="handleFileSelect"
          />

          <div class="dropzone-icon">
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7" d="M12 16V4m0 0-4 4m4-4 4 4M5 18a3 3 0 0 0 3 3h8a3 3 0 0 0 3-3" />
            </svg>
          </div>

          <div class="dropzone-copy">
            <p class="dropzone-title">{{ uploadTitle }}</p>
            <p class="dropzone-body">{{ uploading && fileName ? fileName : t('uploadBody') }}</p>
            <p class="dropzone-meta">{{ t('uploadHint') }}</p>
          </div>

          <button type="button" class="primary-button" :disabled="uploading">
            {{ uploading ? t('uploadingLabel') : t('chooseFile') }}
          </button>
        </div>

        <aside class="settings-pane">
          <div>
            <p class="settings-title">{{ t('settingsLabel') }}</p>
            <p class="settings-copy">{{ t('uploadPanelBody') }}</p>
          </div>

          <div class="field">
            <span class="field-label">{{ t('languageLabel') }}</span>
            <div class="choice-group">
              <button
                v-for="option in languageOptions"
                :key="`lang-${option.value}`"
                type="button"
                class="choice-chip"
                :class="{ 'choice-chip-active': language === option.value }"
                @click="language = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <div class="field">
            <span class="field-label">{{ t('speakerLabel') }}</span>
            <div class="choice-group choice-group-compact">
              <button
                v-for="option in speakerOptions"
                :key="`speaker-${option.value || 'auto'}`"
                type="button"
                class="choice-chip"
                :class="{ 'choice-chip-active': speakerCount === option.value }"
                @click="speakerCount = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <div v-if="error" class="error-note">
            {{ error }}
          </div>
        </aside>
      </div>
    </section>

    <section class="surface current-surface">
      <div class="section-head">
        <div>
          <h2 class="section-title">{{ t('homeFocusTitle') }}</h2>
          <p class="section-copy">{{ focusTask ? t('homeFocusBody') : t('homeFocusEmptyBody') }}</p>
        </div>
      </div>

      <div v-if="focusTask" class="current-body">
        <div class="current-top">
          <div>
            <p class="current-name">{{ focusTask.filename }}</p>
            <p class="current-meta">{{ formatDate(focusTask.created_at) }}</p>
          </div>

          <div class="current-actions">
            <span class="status-pill" :class="`status-pill-${focusTask.status}`">
              {{ getStatusText(focusTask) }}
            </span>
            <button class="secondary-button" @click="handleSelect(focusTask)">
              {{ t('openTask') }}
            </button>
            <button
              v-if="focusTask.status === 'failed'"
              class="secondary-button"
              :disabled="retryingTaskId === focusTask.task_id"
              @click="handleRetry(focusTask)"
            >
              {{ retryingTaskId === focusTask.task_id ? t('retrying') : t('retry') }}
            </button>
            <button class="secondary-button" @click="handleDelete(focusTask)">
              {{ t('delete') }}
            </button>
          </div>
        </div>

        <div class="current-stats">
          <article class="info-card">
            <span>{{ t('listStage') }}</span>
            <strong>{{ focusTask.stage ? getStageText(focusTask.stage) : '--' }}</strong>
          </article>
          <article class="info-card">
            <span>{{ t('listTiming') }}</span>
            <strong>{{ getTimingText(focusTask) }}</strong>
          </article>
          <article class="info-card">
            <span>{{ t('languageLabel') }}</span>
            <strong>{{ focusTask.language || '--' }}</strong>
          </article>
          <article class="info-card">
            <span>{{ t('speakerLabel') }}</span>
            <strong>{{ focusTask.speaker_count || '--' }}</strong>
          </article>
        </div>

        <p v-if="focusTask.status === 'failed' && focusTask.error_message" class="current-error">
          {{ focusTask.error_message }}
        </p>

        <div v-if="focusTask.status === 'processing'" class="current-progress">
          <div class="progress-track">
            <div class="progress-bar" :style="{ width: `${focusTask.progress}%` }"></div>
          </div>
          <span class="progress-value">{{ focusTask.progress }}%</span>
        </div>
      </div>

      <div v-else class="empty-shell">
        <p class="empty-title">{{ t('homeFocusEmptyTitle') }}</p>
        <p class="empty-copy">{{ t('homeFocusEmptyBody') }}</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '../stores/task'
import { useLocale } from '../composables/useLocale'

const router = useRouter()
const taskStore = useTaskStore()
const { locale, t } = useLocale()

const fileInput = ref(null)
const isDragging = ref(false)
const fileName = ref('')
const uploading = ref(false)
const refreshInterval = ref(null)
const retryingTaskId = ref('')
const language = ref('auto')
const speakerCount = ref('')

const acceptTypes = '.mp3,.wav,.m4a,.webm,.ogg,.flac,.aac'
const tasks = computed(() => taskStore.tasks)
const error = computed(() => taskStore.error)
const activeTasks = computed(() => tasks.value.filter((task) => ['pending', 'processing'].includes(task.status)))
const focusTask = computed(() => activeTasks.value[0] || taskStore.currentTask || tasks.value[0] || null)
const languageOptions = computed(() => ([
  { value: 'auto', label: t('languageAuto') },
  { value: 'zh', label: t('languageZh') },
  { value: 'en', label: t('languageEn') },
]))
const speakerOptions = computed(() => ([
  { value: '', label: t('speakerAuto') },
  { value: '2', label: t('speakerTwo') },
  { value: '3', label: t('speakerThree') },
  { value: '4', label: t('speakerFour') },
]))

const uploadTitle = computed(() => {
  if (uploading.value) return t('uploadTitleUploading')
  if (isDragging.value) return t('uploadTitleDragging')
  return t('uploadTitleIdle')
})

onMounted(async () => {
  await taskStore.fetchTasks({ page: 1 })
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
    const hasActive = tasks.value.some((task) => ['pending', 'processing'].includes(task.status))
    if (hasActive) {
      taskStore.fetchTasks({ page: 1 })
    }
  }, 5000)
}

function handleDrop(event) {
  isDragging.value = false
  const files = event.dataTransfer.files
  if (files.length > 0) processFile(files[0])
}

function handleFileSelect(event) {
  const files = event.target.files
  if (files.length > 0) processFile(files[0])
  event.target.value = ''
}

async function processFile(file) {
  fileName.value = file.name
  uploading.value = true

  try {
    const options = { language: language.value }
    if (speakerCount.value) {
      options.speaker_count = Number(speakerCount.value)
    }

    const task = await taskStore.createTask(file, options)
    if (task?.task_id) {
      router.push({ name: 'task-detail', params: { id: task.task_id } })
    }
  } finally {
    uploading.value = false
  }
}

function handleSelect(task) {
  taskStore.setCurrentTask(task)
  router.push({ name: 'task-detail', params: { id: task.task_id } })
}

async function handleDelete(task) {
  const confirmed = window.confirm(t('confirmDelete', { filename: task.filename }))
  if (!confirmed) return
  await taskStore.deleteTask(task.task_id)
  await taskStore.fetchTasks({ page: 1 })
}

async function handleRetry(task) {
  retryingTaskId.value = task.task_id
  try {
    await taskStore.retryTask(task.task_id)
    await taskStore.fetchTasks({ page: 1 })
  } finally {
    retryingTaskId.value = ''
  }
}

function getStatusText(task) {
  if (task.status === 'processing' && task.stage === 'queued') return t('queuedBadge')
  return {
    pending: t('pendingBadge'),
    processing: t('processingBadge'),
    completed: t('completedBadge'),
    failed: t('failedBadge'),
  }[task.status] || task.status
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
</script>

<style scoped>
.home-page {
  @apply space-y-5 pb-10;
}

.surface {
  @apply overflow-hidden rounded-[24px] border bg-white;
  border-color: var(--line);
  box-shadow: var(--shadow-soft);
}

.surface-head,
.section-head {
  @apply flex flex-col gap-5 border-b px-5 py-5 md:px-6;
  border-color: var(--line);
}

.eyebrow,
.info-card span {
  @apply text-xs font-medium uppercase tracking-[0.08em] text-[var(--muted)];
  font-family: var(--font-mono);
}

.hero-title {
  @apply mt-2 text-[1.85rem] font-semibold tracking-tight text-[var(--text-strong)];
}

.surface-copy,
.section-copy,
.settings-copy,
.dropzone-body,
.dropzone-meta,
.current-meta,
.empty-copy,
.field-label {
  @apply text-sm leading-6 text-[var(--muted)];
}

.upload-grid {
  @apply grid gap-0 xl:grid-cols-[minmax(0,1fr)_280px];
}

.dropzone {
  @apply flex min-h-[320px] cursor-pointer flex-col justify-between border-b px-5 py-5 transition-all duration-200 xl:border-b-0 xl:border-r xl:px-6;
  border-color: var(--line);
  background: linear-gradient(180deg, #ffffff 0%, #f8f8fa 100%);
}

.dropzone-active {
  box-shadow: inset 0 0 0 1px rgba(0, 113, 227, 0.2);
}

.dropzone-disabled {
  @apply cursor-progress opacity-75;
}

.dropzone-icon {
  @apply flex h-11 w-11 items-center justify-center rounded-full;
  background: rgba(0, 113, 227, 0.08);
  color: var(--accent);
}

.dropzone-copy {
  @apply mt-8 max-w-xl;
}

.dropzone-title {
  @apply text-[1.65rem] font-semibold tracking-tight text-[var(--text-strong)];
}

.primary-button,
.secondary-button {
  @apply inline-flex items-center justify-center rounded-full px-4 text-sm font-medium transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-45;
  height: 2.5rem;
  white-space: nowrap;
}

.primary-button {
  @apply mt-6 text-white;
  background: var(--accent);
}

.primary-button:hover {
  background: var(--accent-strong);
}

.secondary-button {
  border: 1px solid var(--line-strong);
  background: white;
  color: var(--text-strong);
}

.secondary-button:hover {
  border-color: rgba(0, 113, 227, 0.24);
  color: var(--accent);
}

.settings-pane {
  @apply flex flex-col gap-4 px-5 py-5 xl:px-6;
  background: rgba(247, 247, 249, 0.72);
}

.settings-title,
.section-title {
  @apply text-base font-semibold tracking-tight text-[var(--text-strong)];
}

.field {
  @apply flex flex-col gap-2;
}

.choice-group {
  @apply flex flex-wrap gap-2;
}

.choice-group-compact {
  @apply gap-2;
}

.choice-chip {
  @apply inline-flex items-center justify-center rounded-full border px-3.5 py-2 text-sm font-medium transition-colors duration-200;
  border-color: var(--line);
  background: white;
  color: var(--muted);
}

.choice-chip:hover {
  border-color: rgba(0, 113, 227, 0.22);
  color: var(--text-strong);
}

.choice-chip-active {
  border-color: rgba(0, 113, 227, 0.18);
  background: rgba(0, 113, 227, 0.1);
  color: var(--accent);
}

.error-note {
  @apply rounded-xl px-4 py-3 text-sm leading-6;
  background: rgba(255, 59, 48, 0.08);
  color: var(--danger);
}

.current-body {
  @apply px-5 py-5 md:px-6;
}

.current-top {
  @apply flex flex-col gap-4 md:flex-row md:items-start md:justify-between;
}

.current-name {
  @apply text-lg font-semibold tracking-tight text-[var(--text-strong)];
}

.current-actions {
  @apply flex flex-wrap items-center gap-2;
}

.status-pill {
  @apply inline-flex h-fit items-center rounded-full px-3 py-1 text-xs font-medium;
}

.status-pill-pending {
  background: rgba(100, 116, 139, 0.12);
  color: #475569;
}

.status-pill-processing {
  background: rgba(0, 113, 227, 0.12);
  color: var(--accent);
}

.status-pill-completed {
  background: rgba(5, 150, 105, 0.12);
  color: var(--success);
}

.status-pill-failed {
  background: rgba(255, 59, 48, 0.12);
  color: var(--danger);
}

.current-stats {
  @apply mt-5 grid gap-3 md:grid-cols-2;
}

.info-card {
  @apply rounded-2xl border px-4 py-4;
  border-color: var(--line);
  background: var(--surface-alt);
}

.info-card strong {
  @apply mt-2 block text-sm font-medium text-[var(--text-strong)];
}

.current-error {
  @apply mt-4 text-sm leading-6;
  color: var(--danger);
}

.current-progress {
  @apply mt-5 flex items-center gap-3;
}

.progress-track {
  @apply h-[4px] flex-1 overflow-hidden rounded-full;
  background: rgba(0, 113, 227, 0.12);
}

.progress-bar {
  @apply h-full rounded-full transition-all duration-500;
  background: var(--accent);
}

.progress-value {
  @apply text-sm font-medium text-[var(--accent)];
}

.empty-shell {
  @apply flex min-h-[220px] flex-col items-center justify-center gap-3 px-6 text-center;
}

.empty-title {
  @apply text-lg font-medium text-[var(--text-strong)];
}
</style>
