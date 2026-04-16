<template>
  <div class="detail-page">
    <div v-if="loading" class="state-shell">
      <div class="loader"></div>
    </div>

    <div v-else-if="task" class="detail-grid">
      <section class="main-column">
        <!-- Header -->
        <header class="detail-header">
          <div>
            <h1 class="detail-title">{{ task.filename }}</h1>
            <p class="detail-copy">{{ leadCopy }}</p>
          </div>

          <div class="detail-header-actions">
            <span class="status-badge" :class="`status-badge-${task.status}`">
              {{ getStatusText(task.status) }}
            </span>
            <button
              v-if="task.status === 'failed'"
              class="btn-secondary"
              :disabled="retrying"
              @click="handleRetry"
            >
              {{ retrying ? t('retrying') : t('retry') }}
            </button>
          </div>
        </header>

        <!-- Progress -->
        <section v-if="task.status === 'pending' || task.status === 'processing'" class="card progress-card">
          <div class="progress-head">
            <div>
              <p class="progress-label-text">{{ t('detailProgressTitle') }}</p>
              <strong class="progress-value">{{ task.progress }}%</strong>
            </div>
          </div>

          <p class="progress-copy">
            {{ task.stage_description || getStageText(task.stage) || t('detailProgressFallback') }}
          </p>

          <div class="progress-track">
            <div class="progress-bar" :style="{ width: `${task.progress}%` }"></div>
          </div>

          <p v-if="task.estimated_remaining" class="progress-meta">
            {{ t('detailRemaining', { value: formatDuration(task.estimated_remaining) }) }}
          </p>
        </section>

        <!-- Error -->
        <section v-if="task.status === 'failed'" class="card alert-card">
          <div class="alert-content">
            <svg class="alert-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <div>
              <p class="alert-text">{{ task.error_message || t('detailFailedFallback') }}</p>
              <p v-if="task.last_error_stage" class="alert-meta">
                {{ t('detailFailureStage') }} · {{ getStageText(task.last_error_stage) }}
              </p>
            </div>
          </div>
          <button class="btn-secondary" :disabled="retrying" @click="handleRetry">
            {{ retrying ? t('retrying') : t('retry') }}
          </button>
        </section>

        <!-- Page error -->
        <section v-if="pageError" class="card alert-card">
          <p class="alert-text">{{ pageError }}</p>
        </section>

        <!-- Results tabs -->
        <template v-if="task.status === 'completed' && minutes">
          <div class="tab-bar">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              class="tab-btn"
              :class="{ 'tab-btn-active': activeTab === tab.id }"
              @click="activeTab = tab.id"
            >
              {{ tab.label }}
            </button>
          </div>

          <!-- Minutes tab -->
          <section v-show="activeTab === 'minutes'" class="card">
            <div class="reader-section">
              <p class="reader-label">{{ t('minutesSummary') }}</p>
              <p class="reader-text">{{ minutes.minutes?.summary || t('noMinutes') }}</p>
            </div>

            <div v-if="minutes.minutes?.key_points?.length" class="reader-section">
              <p class="reader-label">{{ t('minutesKeyPoints') }}</p>
              <ul class="reader-list">
                <li v-for="(point, index) in minutes.minutes.key_points" :key="index">
                  <strong>{{ point.title }}</strong>
                  <span>{{ point.content }}</span>
                </li>
              </ul>
            </div>

            <div v-if="minutes.minutes?.action_items?.length" class="reader-section">
              <p class="reader-label">{{ t('minutesActions') }}</p>
              <ul class="reader-list">
                <li v-for="(item, index) in minutes.minutes.action_items" :key="index">
                  <strong>{{ item.assignee || '-' }}</strong>
                  <span>{{ item.task }}<template v-if="item.deadline"> · {{ item.deadline }}</template></span>
                </li>
              </ul>
            </div>

            <div v-if="minutes.minutes?.decisions?.length" class="reader-section">
              <p class="reader-label">{{ t('minutesDecisions') }}</p>
              <ul class="reader-list">
                <li v-for="(decision, index) in minutes.minutes.decisions" :key="index">
                  <strong>{{ decision.topic }}</strong>
                  <span>{{ decision.decision }}</span>
                </li>
              </ul>
            </div>
          </section>

          <!-- Transcript tab -->
          <section v-show="activeTab === 'transcript'" class="card">
            <div v-if="minutes.transcript?.segments?.length" class="transcript-list">
              <article
                v-for="(segment, index) in minutes.transcript.segments"
                :key="index"
                class="transcript-row"
              >
                <div class="transcript-meta">
                  <span class="speaker-chip">{{ segment.speaker_label || segment.speaker }}</span>
                  <span class="time-chip">{{ formatTime(segment.start_time) }}</span>
                </div>
                <p class="transcript-text">{{ segment.text }}</p>
              </article>
            </div>

            <div v-else class="empty-section">
              <p>{{ t('noTranscript') }}</p>
            </div>
          </section>
        </template>

        <section v-else-if="task.status === 'completed'" class="card empty-section">
          <p>{{ t('noMinutes') }}</p>
        </section>
      </section>

      <!-- Side column -->
      <aside class="side-column">
        <section class="card side-card">
          <div class="side-card-header">
            <h2 class="side-card-title">{{ t('detailSummaryTitle') }}</h2>
          </div>

          <div class="info-list">
            <div class="info-row">
              <span>{{ t('detailStatusLabel') }}</span>
              <strong>{{ getStatusText(task.status) }}</strong>
            </div>
            <div class="info-row">
              <span>{{ t('detailStageLabel') }}</span>
              <strong>{{ task.stage ? getStageText(task.stage) : '--' }}</strong>
            </div>
            <div class="info-row">
              <span>{{ t('detailCreatedLabel') }}</span>
              <strong>{{ formatDate(task.created_at) }}</strong>
            </div>
            <div class="info-row">
              <span>{{ t('detailProcessingCount') }}</span>
              <strong>{{ task.attempt_count || 0 }}</strong>
            </div>
            <div class="info-row">
              <span>{{ t('detailQueueTime') }}</span>
              <strong>{{ formatDuration(task.queue_seconds) }}</strong>
            </div>
            <div class="info-row">
              <span>{{ t('detailProcessingTime') }}</span>
              <strong>{{ formatDuration(task.processing_seconds) }}</strong>
            </div>
            <div v-if="task.duration" class="info-row">
              <span>{{ t('detailAudioDuration') }}</span>
              <strong>{{ formatDuration(task.duration) }}</strong>
            </div>
            <div class="info-row">
              <span>{{ t('detailLanguageSetting') }}</span>
              <strong>{{ task.language || '--' }}</strong>
            </div>
            <div class="info-row">
              <span>{{ t('detailSpeakerSetting') }}</span>
              <strong>{{ task.speaker_count || '--' }}</strong>
            </div>
            <div v-if="minutes?.transcript?.segments?.length" class="info-row">
              <span>{{ t('detailTranscriptCount') }}</span>
              <strong>{{ formatNumber(minutes.transcript.segments.length) }}</strong>
            </div>
            <div v-if="task.last_error_label" class="info-row">
              <span>{{ t('detailFailureType') }}</span>
              <strong>{{ task.last_error_label }}</strong>
            </div>
          </div>
        </section>

        <section v-if="minutes?.model_used || minutes?.tokens_used" class="card side-card">
          <div class="side-card-header">
            <h2 class="side-card-title">{{ t('detailOutputTitle') }}</h2>
          </div>

          <div class="info-list">
            <div class="info-row">
              <span>{{ t('detailLlm') }}</span>
              <strong>{{ minutes?.model_used || t('modelUnknown') }}</strong>
            </div>
            <div v-if="minutes?.tokens_used" class="info-row">
              <span>{{ t('tokenLabel') }}</span>
              <strong>{{ formatNumber(minutes.tokens_used) }}</strong>
            </div>
          </div>
        </section>
      </aside>
    </div>

    <!-- Not found -->
    <div v-else-if="notFound" class="state-shell">
      <p class="state-title">{{ t('detailMissing') }}</p>
      <router-link to="/tasks" class="btn-secondary mt-4">{{ t('detailBack') }}</router-link>
    </div>

    <!-- Error state -->
    <div v-else class="state-shell">
      <p class="state-title">{{ t('detailUnavailable') }}</p>
      <button class="btn-secondary mt-4" @click="loadTask">{{ t('detailRetryLoad') }}</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTaskStore } from '../stores/task'
import { useLocale } from '../composables/useLocale'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()
const { locale, t } = useLocale()

const loading = ref(true)
const minutes = ref(null)
const activeTab = ref('minutes')
const pageError = ref('')
const notFound = ref(false)
const retrying = ref(false)
const task = computed(() => taskStore.currentTask)
const taskId = computed(() => route.params.id)

const tabs = computed(() => ([
  { id: 'minutes', label: t('tabMinutes') },
  { id: 'transcript', label: t('tabTranscript') },
]))

const leadCopy = computed(() => {
  if (!task.value) return ''
  if (task.value.status === 'pending') return t('detailLeadPending')
  if (task.value.status === 'processing') return t('detailLeadProcessing')
  if (task.value.status === 'completed') return t('detailLeadCompleted')
  if (task.value.status === 'failed') return task.value.error_message || t('detailLeadFailed')
  return ''
})

watch(() => task.value?.status, async (newStatus, oldStatus) => {
  if (!newStatus) return

  if (newStatus === 'completed' && oldStatus !== 'completed') {
    await loadMinutes()
    taskStore.stopProgressPolling()
  } else if (['pending', 'processing'].includes(newStatus)) {
    taskStore.startProgressPolling(taskId.value)
  } else if (newStatus === 'failed') {
    taskStore.stopProgressPolling()
  }
})

watch(taskId, async () => {
  await loadTask()
})

onMounted(async () => {
  await loadTask()
})

onUnmounted(() => {
  taskStore.stopProgressPolling()
})

async function loadTask() {
  loading.value = true
  pageError.value = ''
  minutes.value = null
  notFound.value = false

  try {
    const detail = await taskStore.fetchTask(taskId.value)
    if (detail.status === 'pending' || detail.status === 'processing') {
      taskStore.startProgressPolling(taskId.value)
    }
    if (detail.status === 'completed') {
      await loadMinutes()
    }
  } catch (error) {
    pageError.value = error.message
    notFound.value = error.status === 404
    if (notFound.value) {
      taskStore.clearCurrentTask()
    }
  } finally {
    loading.value = false
  }
}

async function loadMinutes() {
  try {
    pageError.value = ''
    minutes.value = await taskStore.fetchMinutes(taskId.value)
  } catch (error) {
    pageError.value = error.message
  }
}

async function handleRetry() {
  retrying.value = true
  pageError.value = ''
  minutes.value = null

  try {
    const retriedTask = await taskStore.retryTask(taskId.value)
    if (retriedTask?.status === 'pending' || retriedTask?.status === 'processing') {
      taskStore.startProgressPolling(taskId.value)
    }
  } catch (error) {
    pageError.value = error.message
  } finally {
    retrying.value = false
  }
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

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleString(locale.value === 'zh' ? 'zh-CN' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatDuration(value) {
  if (value == null) return '--'
  const rounded = Math.max(0, Math.round(value))
  if (rounded < 60) return locale.value === 'zh' ? `${rounded} 秒` : `${rounded}s`
  const minutes = Math.floor(rounded / 60)
  const seconds = rounded % 60
  if (minutes < 60) {
    return locale.value === 'zh'
      ? (seconds ? `${minutes} 分 ${seconds} 秒` : `${minutes} 分`)
      : (seconds ? `${minutes}m ${seconds}s` : `${minutes}m`)
  }
  const hours = Math.floor(minutes / 60)
  const remainMinutes = minutes % 60
  return locale.value === 'zh'
    ? (remainMinutes ? `${hours} 时 ${remainMinutes} 分` : `${hours} 时`)
    : (remainMinutes ? `${hours}h ${remainMinutes}m` : `${hours}h`)
}

function formatNumber(value) {
  if (value == null) return '--'
  return new Intl.NumberFormat(locale.value === 'zh' ? 'zh-CN' : 'en-US').format(value)
}

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60)
  const remainSeconds = Math.floor(seconds % 60)
  return `${minutes}:${remainSeconds.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.detail-page {
  @apply pb-10;
}

.detail-grid {
  @apply grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start;
}

.main-column {
  @apply min-w-0 space-y-5;
}

.side-column {
  @apply space-y-5;
}

/* ── Header ── */
.detail-header {
  @apply flex flex-col gap-4 pb-5 md:flex-row md:items-start md:justify-between;
  border-bottom: 1px solid var(--line);
}

.detail-title {
  @apply text-2xl font-semibold tracking-tight;
  color: var(--text-strong);
}

.detail-copy {
  @apply mt-2 max-w-3xl text-sm leading-7;
  color: var(--muted);
}

.detail-header-actions {
  @apply flex items-center gap-3;
}

/* ── Progress card ── */
.progress-card {
  @apply p-5;
}

.progress-head {
  @apply flex items-start justify-between;
}

.progress-label-text {
  @apply text-xs font-medium;
  color: var(--muted);
}

.progress-value {
  @apply mt-1 block text-3xl font-semibold tracking-tight;
  color: var(--text-strong);
}

.progress-copy {
  @apply mt-3 text-sm;
  color: var(--muted);
}

.progress-track {
  @apply mt-4 h-1.5 overflow-hidden rounded-full;
  background: rgba(0, 113, 227, 0.1);
}

.progress-bar {
  @apply h-full rounded-full transition-all duration-500;
  background: var(--accent);
}

.progress-meta {
  @apply mt-3 text-sm;
  color: var(--muted);
}

/* ── Alert card ── */
.alert-card {
  @apply flex flex-col gap-4 p-5 text-sm md:flex-row md:items-center md:justify-between;
  background: rgba(255, 59, 48, 0.03);
  border-color: rgba(255, 59, 48, 0.12);
}

.alert-content {
  @apply flex items-start gap-3;
}

.alert-icon {
  @apply mt-0.5 h-5 w-5 shrink-0;
  color: var(--danger);
}

.alert-text {
  color: var(--text-strong);
}

.alert-meta {
  @apply mt-1 text-xs;
  color: var(--muted);
}

/* ── Tabs ── */
.tab-bar {
  @apply flex gap-2;
}

.tab-btn {
  @apply rounded-lg border px-4 py-2 text-sm font-medium transition-colors duration-150;
  border-color: var(--line);
  background: white;
  color: var(--muted);
}

.tab-btn:hover {
  border-color: rgba(0, 113, 227, 0.2);
  color: var(--text-strong);
}

.tab-btn-active {
  background: var(--text-strong);
  border-color: var(--text-strong);
  color: white;
}

/* ── Reader ── */
.reader-section {
  @apply px-5 py-5;
}

.reader-section + .reader-section {
  border-top: 1px solid var(--line);
}

.reader-label {
  @apply text-xs font-medium uppercase tracking-wider;
  color: var(--muted);
}

.reader-text {
  @apply mt-2 text-sm leading-8;
  color: var(--text-strong);
  white-space: pre-wrap;
}

.reader-list {
  @apply mt-3 space-y-3;
}

.reader-list li {
  @apply grid gap-1 border-b pb-3 text-sm leading-7;
  border-color: var(--line-soft);
  color: var(--text-strong);
}

.reader-list li:last-child {
  @apply border-b-0 pb-0;
}

.reader-list strong {
  @apply font-semibold;
  color: var(--text-strong);
}

/* ── Transcript ── */
.transcript-list > * + * {
  border-top: 1px solid var(--line-soft);
}

.transcript-row {
  @apply grid gap-4 px-5 py-4 md:grid-cols-[140px_1fr];
}

.transcript-meta {
  @apply flex flex-col gap-1.5;
}

.speaker-chip,
.time-chip {
  @apply inline-flex w-fit items-center rounded-md px-2 py-0.5 text-xs;
}

.speaker-chip {
  border: 1px solid var(--line-strong);
  color: var(--text-strong);
}

.time-chip {
  background: var(--surface-alt);
  color: var(--muted);
}

.transcript-text {
  @apply text-sm leading-7;
  color: var(--text-strong);
}

.empty-section {
  @apply p-5 text-sm;
  color: var(--muted);
}

/* ── Side cards ── */
.side-card {
  @apply overflow-hidden;
}

.side-card-header {
  @apply px-5 py-4;
  border-bottom: 1px solid var(--line);
}

.side-card-title {
  @apply text-sm font-semibold;
  color: var(--text-strong);
}

.info-list > * + * {
  border-top: 1px solid var(--line-soft);
}

.info-row {
  @apply flex items-center justify-between gap-4 px-5 py-3 text-sm;
}

.info-row span {
  color: var(--muted);
}

.info-row strong {
  @apply text-right font-medium;
  color: var(--text-strong);
}

/* ── States ── */
.state-shell {
  @apply flex min-h-[240px] flex-col items-center justify-center gap-3 text-center;
}

.state-title {
  @apply text-lg font-medium;
  color: var(--text-strong);
}

.loader {
  @apply h-8 w-8 animate-spin rounded-full border-2 border-t-transparent;
  border-color: var(--accent);
  border-top-color: transparent;
}

@media (min-width: 1280px) {
  .side-column {
    position: sticky;
    top: 4.5rem;
  }
}
</style>
