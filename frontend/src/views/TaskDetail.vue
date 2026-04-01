<template>
  <div class="detail-page">
    <div v-if="loading" class="state-shell">
      <div class="loader"></div>
    </div>

    <div v-else-if="task" class="detail-grid">
      <section class="main-column">
        <button @click="router.push({ name: 'home' })" class="back-link">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
          {{ t('detailBack') }}
        </button>

        <header class="detail-header">
          <div>
            <h1 class="detail-title">{{ task.filename }}</h1>
            <p class="detail-copy">{{ leadCopy }}</p>
          </div>

          <span class="status-pill" :class="`status-pill-${task.status}`">
            {{ getStatusText(task.status) }}
          </span>
        </header>

        <section v-if="task.status === 'pending' || task.status === 'processing'" class="surface progress-surface">
          <div class="progress-head">
            <div>
              <p class="section-label">{{ t('detailProgressTitle') }}</p>
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

        <section v-if="task.status === 'failed'" class="surface alert-surface alert-error">
          <div>
            <p>{{ task.error_message || t('detailFailedFallback') }}</p>
            <p v-if="task.last_error_stage" class="alert-meta">
              {{ t('detailFailureStage') }} · {{ getStageText(task.last_error_stage) }}
            </p>
          </div>

          <button class="secondary-button" :disabled="retrying" @click="handleRetry">
            {{ retrying ? t('retrying') : t('retry') }}
          </button>
        </section>

        <section v-if="pageError" class="surface alert-surface alert-error">
          <p>{{ pageError }}</p>
        </section>

        <template v-if="task.status === 'completed' && minutes">
          <section class="tabbar">
            <div class="tab-group">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                class="tab-button"
                :class="{ 'tab-button-active': activeTab === tab.id }"
                @click="activeTab = tab.id"
              >
                {{ tab.label }}
              </button>
            </div>
          </section>

          <section v-show="activeTab === 'minutes'" class="surface reader-surface">
            <div class="reader-section">
              <p class="section-label">{{ t('minutesSummary') }}</p>
              <h2 class="reader-title">{{ t('minutesSummary') }}</h2>
              <p class="reader-text">{{ minutes.minutes?.summary || t('noMinutes') }}</p>
            </div>

            <div v-if="minutes.minutes?.key_points?.length" class="reader-section">
              <p class="section-label">{{ t('minutesKeyPoints') }}</p>
              <h2 class="reader-title">{{ t('minutesKeyPoints') }}</h2>
              <ul class="reader-list">
                <li v-for="(point, index) in minutes.minutes.key_points" :key="index">
                  <strong>{{ point.title }}</strong>
                  <span>{{ point.content }}</span>
                </li>
              </ul>
            </div>

            <div v-if="minutes.minutes?.action_items?.length" class="reader-section">
              <p class="section-label">{{ t('minutesActions') }}</p>
              <h2 class="reader-title">{{ t('minutesActions') }}</h2>
              <ul class="reader-list">
                <li v-for="(item, index) in minutes.minutes.action_items" :key="index">
                  <strong>{{ item.assignee || '-' }}</strong>
                  <span>{{ item.task }}<template v-if="item.deadline"> · {{ item.deadline }}</template></span>
                </li>
              </ul>
            </div>

            <div v-if="minutes.minutes?.decisions?.length" class="reader-section">
              <p class="section-label">{{ t('minutesDecisions') }}</p>
              <h2 class="reader-title">{{ t('minutesDecisions') }}</h2>
              <ul class="reader-list">
                <li v-for="(decision, index) in minutes.minutes.decisions" :key="index">
                  <strong>{{ decision.topic }}</strong>
                  <span>{{ decision.decision }}</span>
                </li>
              </ul>
            </div>
          </section>

          <section v-show="activeTab === 'transcript'" class="surface reader-surface">
            <header class="reader-section">
              <p class="section-label">{{ t('transcriptHeading') }}</p>
              <h2 class="reader-title">{{ t('transcriptHeading') }}</h2>
            </header>

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
                <p class="transcript-copy">{{ segment.text }}</p>
              </article>
            </div>

            <p v-else class="reader-text reader-empty">{{ t('noTranscript') }}</p>
          </section>
        </template>

        <section v-else-if="task.status === 'completed'" class="surface alert-surface">
          <p>{{ t('noMinutes') }}</p>
        </section>
      </section>

      <aside class="side-column">
        <section class="surface info-surface">
          <div class="surface-head compact-head">
            <h2 class="section-title">{{ t('detailSummaryTitle') }}</h2>
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

        <section class="surface info-surface">
          <div class="surface-head compact-head">
            <h2 class="section-title">{{ t('detailActionsTitle') }}</h2>
          </div>

          <p class="side-copy">{{ t('detailActionsBody') }}</p>

          <button
            v-if="task.status === 'failed'"
            class="secondary-button side-action"
            :disabled="retrying"
            @click="handleRetry"
          >
            {{ retrying ? t('retrying') : t('retry') }}
          </button>
        </section>

        <section v-if="minutes?.model_used || minutes?.tokens_used" class="surface info-surface">
          <div class="surface-head compact-head">
            <h2 class="section-title">{{ t('detailOutputTitle') }}</h2>
          </div>

          <div class="info-list info-list-tight">
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

    <div v-else-if="notFound" class="state-shell">
      <p class="state-title">{{ t('detailMissing') }}</p>
    </div>

    <div v-else class="state-shell">
      <p class="state-title">{{ t('detailUnavailable') }}</p>
      <button class="secondary-button mt-4" @click="loadTask">{{ t('detailRetryLoad') }}</button>
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
  @apply grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px] xl:items-start;
}

.main-column {
  @apply min-w-0 space-y-5;
}

.side-column {
  @apply space-y-5;
}

.back-link {
  @apply inline-flex items-center gap-2 text-sm text-[var(--muted)] transition-colors duration-200 hover:text-[var(--text-strong)];
}

.detail-header {
  @apply flex flex-col gap-4 border-b border-[var(--line)] pb-5 md:flex-row md:items-start md:justify-between;
}

.detail-title {
  @apply text-2xl font-semibold tracking-tight text-[var(--text-strong)] md:text-[2rem];
}

.detail-copy {
  @apply mt-2 max-w-3xl text-sm leading-7 text-[var(--muted)];
}

.surface {
  @apply overflow-hidden rounded-[22px] border;
  border-color: var(--line);
  background: var(--surface);
  box-shadow: var(--shadow-soft);
}

.surface-head {
  @apply border-b px-5 py-4 md:px-6;
  border-color: var(--line);
}

.compact-head {
  @apply border-b-0 pb-3;
}

.section-title {
  @apply text-[1.05rem] font-semibold tracking-tight text-[var(--text-strong)];
}

.section-label {
  @apply text-xs font-medium text-[var(--muted)];
}

.progress-surface,
.alert-surface,
.info-surface {
  @apply px-5 py-5 md:px-6;
}

.progress-value {
  @apply mt-2 block text-4xl font-semibold tracking-tight text-[var(--text-strong)];
}

.progress-copy,
.progress-meta,
.side-copy {
  @apply text-sm leading-7 text-[var(--muted)];
}

.progress-copy {
  @apply mt-4;
}

.progress-track {
  @apply mt-5 h-[5px] overflow-hidden rounded-full;
  background: rgba(0, 113, 227, 0.12);
}

.progress-bar {
  @apply h-full rounded-full transition-all duration-500;
  background: var(--accent);
}

.progress-meta {
  @apply mt-3;
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

.alert-surface {
  @apply flex flex-col gap-4 text-sm leading-6 text-[var(--text-strong)] md:flex-row md:items-center md:justify-between;
}

.alert-error {
  background: rgba(255, 59, 48, 0.04);
  border-color: rgba(255, 59, 48, 0.16);
}

.alert-meta {
  @apply mt-1 text-xs text-[var(--muted)];
}

.tabbar {
  @apply border-b border-[var(--line)] pb-4;
}

.tab-group {
  @apply flex flex-wrap gap-2;
}

.tab-button,
.secondary-button {
  @apply inline-flex items-center justify-center rounded-full px-4 text-sm font-medium transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-45;
  height: 2.5rem;
}

.tab-button {
  @apply border;
  border-color: var(--line-strong);
  background: white;
  color: var(--muted);
}

.tab-button-active {
  background: var(--text-strong);
  border-color: var(--text-strong);
  color: white;
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

.reader-section {
  @apply px-5 py-5 md:px-6;
}

.reader-section + .reader-section {
  @apply border-t;
  border-color: var(--line);
}

.reader-title {
  @apply mt-1 text-[1.05rem] font-semibold tracking-tight text-[var(--text-strong)];
}

.reader-text,
.transcript-copy {
  @apply text-sm leading-8 text-[var(--text-strong)];
}

.reader-text {
  @apply mt-3;
  white-space: pre-wrap;
}

.reader-empty {
  @apply px-5 py-5 md:px-6;
}

.reader-list {
  @apply mt-4 space-y-4;
}

.reader-list li {
  @apply grid gap-1 border-b pb-4 text-sm leading-7 text-[var(--text-strong)];
  border-color: var(--line-soft);
}

.reader-list li:last-child {
  @apply border-b-0 pb-0;
}

.reader-list strong {
  @apply font-semibold text-[var(--text-strong)];
}

.transcript-list > * + * {
  border-top: 1px solid var(--line-soft);
}

.transcript-row {
  @apply grid gap-5 px-5 py-5 md:grid-cols-[160px_1fr] md:px-6;
}

.transcript-meta {
  @apply flex flex-col gap-2;
}

.speaker-chip,
.time-chip {
  @apply inline-flex w-fit items-center rounded-full px-3 py-1 text-xs;
}

.speaker-chip {
  border: 1px solid var(--line-strong);
  color: var(--text-strong);
}

.time-chip {
  background: var(--surface-alt);
  color: var(--muted);
}

.info-list {
  @apply mt-1;
}

.info-list-top {
  @apply mt-0;
}

.info-list > * + * {
  border-top: 1px solid var(--line-soft);
}

.info-row {
  @apply flex items-center justify-between gap-4 py-3 text-sm;
}

.info-row span,
.side-copy {
  @apply text-[var(--muted)];
}

.info-row strong {
  @apply text-right text-[var(--text-strong)];
}

.side-copy {
  @apply px-5 md:px-6;
}

.side-action {
  @apply mx-5 mb-5 mt-4 md:mx-6;
}

.state-shell {
  @apply flex min-h-[240px] flex-col items-center justify-center gap-3 text-center;
}

.state-title {
  @apply text-lg font-medium text-[var(--text-strong)];
}

.loader {
  @apply h-9 w-9 animate-spin rounded-full border-2 border-t-transparent;
  border-color: var(--accent);
  border-top-color: transparent;
}

@media (min-width: 1280px) {
  .side-column {
    position: sticky;
    top: 1.75rem;
  }
}
</style>
