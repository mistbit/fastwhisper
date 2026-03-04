<template>
  <div class="max-w-4xl mx-auto">
    <!-- Back -->
    <button @click="router.back()" class="back-btn">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      返回
    </button>

    <!-- Loading -->
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
    </div>

    <!-- Content -->
    <div v-else-if="task" class="space-y-6">
      <!-- Header -->
      <div class="task-header-card">
        <div>
          <h1 class="task-title">{{ task.filename }}</h1>
          <p class="task-date">{{ formatDate(task.created_at) }}</p>
        </div>
        <span class="status-badge" :class="`status-${task.status}`">
          {{ getStatusText(task.status) }}
        </span>
      </div>

      <!-- Progress -->
      <div v-if="task.status === 'processing' || task.status === 'pending'" class="progress-card">
        <div class="progress-header">
          <span class="progress-label">{{ task.stage_description || '准备处理...' }}</span>
          <span class="progress-value">{{ task.progress }}%</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${task.progress}%` }"></div>
        </div>
        <p v-if="task.estimated_remaining" class="progress-time">
          预计剩余 {{ formatDuration(task.estimated_remaining) }}
        </p>
      </div>

      <!-- Error -->
      <div v-if="task.status === 'failed'" class="error-card">
        <svg class="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="text-red-400 text-sm">{{ task.error_message || '处理失败' }}</span>
      </div>

      <!-- Results -->
      <template v-if="task.status === 'completed' && minutes">
        <!-- Tabs -->
        <div class="tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="tab"
            :class="{ 'tab-active': activeTab === tab.id }"
            @click="activeTab = tab.id"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- Minutes -->
        <div v-show="activeTab === 'minutes'" class="space-y-6">
          <!-- Summary -->
          <section v-if="minutes.minutes?.summary" class="result-section">
            <h3 class="section-title">
              <span class="section-icon bg-primary-500/10 text-primary-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </span>
              摘要
            </h3>
            <p class="text-dark-300 leading-relaxed">{{ minutes.minutes.summary }}</p>
          </section>

          <!-- Key Points -->
          <section v-if="minutes.minutes?.key_points?.length" class="result-section">
            <h3 class="section-title">
              <span class="section-icon bg-yellow-500/10 text-yellow-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </span>
              关键要点
            </h3>
            <div class="key-points">
              <div v-for="(point, i) in minutes.minutes.key_points" :key="i" class="key-point-item">
                <span class="key-point-num">{{ i + 1 }}</span>
                <div>
                  <h4 class="text-dark-100 font-medium">{{ point.title }}</h4>
                  <p class="text-sm text-dark-400 mt-1">{{ point.content }}</p>
                </div>
              </div>
            </div>
          </section>

          <!-- Action Items -->
          <section v-if="minutes.minutes?.action_items?.length" class="result-section">
            <h3 class="section-title">
              <span class="section-icon bg-emerald-500/10 text-emerald-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </span>
              待办事项
            </h3>
            <div class="action-list">
              <div v-for="(item, i) in minutes.minutes.action_items" :key="i" class="action-item">
                <span class="action-dot"></span>
                <span class="flex-1 text-dark-200">{{ item.task }}</span>
                <span v-if="item.assignee" class="action-assignee">{{ item.assignee }}</span>
                <span v-if="item.deadline" class="action-deadline">{{ item.deadline }}</span>
              </div>
            </div>
          </section>

          <!-- Decisions -->
          <section v-if="minutes.minutes?.decisions?.length" class="result-section">
            <h3 class="section-title">
              <span class="section-icon bg-purple-500/10 text-purple-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </span>
              决策
            </h3>
            <div class="decision-list">
              <div v-for="(d, i) in minutes.minutes.decisions" :key="i" class="decision-item">
                <h4 class="decision-topic">{{ d.topic }}</h4>
                <p class="text-dark-200">{{ d.decision }}</p>
              </div>
            </div>
          </section>
        </div>

        <!-- Transcript -->
        <div v-show="activeTab === 'transcript'" class="transcript-list">
          <div v-for="(seg, i) in minutes.transcript?.segments" :key="i" class="transcript-item">
            <div class="speaker-avatar">
              {{ getSpeakerInitial(seg.speaker_label || seg.speaker) }}
            </div>
            <div class="transcript-content">
              <div class="transcript-header">
                <span class="speaker-name">{{ seg.speaker_label || seg.speaker }}</span>
                <span class="transcript-time">{{ formatTime(seg.start_time) }}</span>
              </div>
              <p class="transcript-text">{{ seg.text }}</p>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Not Found -->
    <div v-else class="not-found">
      <p class="text-dark-400">任务不存在</p>
      <button @click="router.push('/')" class="mt-4 btn-primary">返回首页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTaskStore } from '../stores/task'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()

const loading = ref(true)
const task = ref(null)
const minutes = ref(null)
const activeTab = ref('minutes')
const taskId = route.params.id

const tabs = [
  { id: 'minutes', label: '会议纪要' },
  { id: 'transcript', label: '转录文本' },
]

watch(() => task.value?.status, async (newStatus, oldStatus) => {
  if (newStatus === 'completed' && oldStatus !== 'completed') {
    await loadMinutes()
  }
})

onMounted(async () => { await loadTask() })
onUnmounted(() => { taskStore.stopProgressPolling() })

async function loadTask() {
  loading.value = true
  try {
    let foundTask = taskStore.tasks.find(t => t.task_id === taskId)
    if (!foundTask) {
      const progress = await taskStore.fetchProgress(taskId)
      if (progress) foundTask = progress
    }
    task.value = foundTask
    if (task.value) {
      if (task.value.status === 'pending' || task.value.status === 'processing') {
        taskStore.startProgressPolling(taskId)
      }
      if (task.value.status === 'completed') {
        await loadMinutes()
      }
    }
  } finally {
    loading.value = false
  }
}

async function loadMinutes() {
  try {
    minutes.value = await taskStore.fetchMinutes(taskId)
  } catch (e) {
    console.error('Failed to load minutes:', e)
  }
}

function getStatusText(s) {
  return { pending: '等待中', processing: '处理中', completed: '已完成', failed: '失败' }[s] || s
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleString('zh-CN')
}

function formatDuration(sec) {
  if (sec < 60) return `${sec} 秒`
  const m = Math.floor(sec / 60), s = sec % 60
  if (m < 60) return `${m} 分 ${s} 秒`
  return `${Math.floor(m / 60)} 时 ${m % 60} 分`
}

function formatTime(s) {
  const m = Math.floor(s / 60), sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

function getSpeakerInitial(speaker) {
  if (!speaker) return '?'
  const m = speaker.match(/\d+/)
  return m ? m[1] : speaker.slice(0, 2).toUpperCase()
}
</script>

<style scoped>
.back-btn {
  @apply inline-flex items-center gap-1 px-3 py-1.5 text-sm text-dark-400 hover:text-dark-200 transition-colors mb-6;
}

.loading-container {
  @apply py-20 text-center;
}

.loading-spinner {
  @apply w-10 h-10 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto;
}

.task-header-card {
  @apply flex items-start justify-between p-5 bg-dark-800/30 border border-dark-700/50 rounded-2xl;
}

.task-title {
  @apply text-xl font-semibold text-dark-100;
}

.task-date {
  @apply text-sm text-dark-500 mt-1;
}

.status-badge {
  @apply px-3 py-1 rounded-full text-xs font-medium;
}

.status-pending { @apply bg-yellow-500/10 text-yellow-400; }
.status-processing { @apply bg-primary-500/10 text-primary-400; }
.status-completed { @apply bg-emerald-500/10 text-emerald-400; }
.status-failed { @apply bg-red-500/10 text-red-400; }

.progress-card {
  @apply p-5 bg-dark-800/30 border border-dark-700/50 rounded-2xl;
}

.progress-header {
  @apply flex items-center justify-between mb-3;
}

.progress-label {
  @apply text-sm text-dark-400;
}

.progress-value {
  @apply text-sm font-medium text-primary-400;
}

.progress-track {
  @apply h-1.5 bg-dark-700 rounded-full overflow-hidden;
}

.progress-fill {
  @apply h-full bg-gradient-to-r from-primary-500 to-primary-400 transition-all duration-500;
}

.progress-time {
  @apply mt-3 text-xs text-dark-500;
}

.error-card {
  @apply flex items-center gap-3 p-4 bg-red-500/5 border border-red-500/10 rounded-xl;
}

.tabs {
  @apply flex gap-1 p-1 bg-dark-800/50 rounded-xl w-fit;
}

.tab {
  @apply px-4 py-2 text-sm font-medium rounded-lg transition-colors text-dark-400 hover:text-dark-200;
}

.tab-active {
  @apply bg-dark-700 text-dark-100;
}

.result-section {
  @apply p-5 bg-dark-800/30 border border-dark-700/50 rounded-2xl;
}

.section-title {
  @apply flex items-center gap-2 text-sm font-medium text-dark-200 mb-4;
}

.section-icon {
  @apply w-6 h-6 rounded-lg flex items-center justify-center;
}

.key-points {
  @apply space-y-3;
}

.key-point-item {
  @apply flex gap-3 p-3 bg-dark-700/20 rounded-xl;
}

.key-point-num {
  @apply flex-shrink-0 w-6 h-6 rounded-full bg-yellow-500/20 text-yellow-400 flex items-center justify-center text-xs font-medium;
}

.action-list {
  @apply space-y-2;
}

.action-item {
  @apply flex items-center gap-3 p-3 bg-dark-700/20 rounded-xl;
}

.action-dot {
  @apply w-2 h-2 rounded-full bg-emerald-400;
}

.action-assignee {
  @apply text-sm text-primary-400;
}

.action-deadline {
  @apply text-sm text-dark-500;
}

.decision-list {
  @apply space-y-3;
}

.decision-item {
  @apply p-4 bg-purple-500/5 border border-purple-500/10 rounded-xl;
}

.decision-topic {
  @apply text-sm font-medium text-purple-400 mb-1;
}

.transcript-list {
  @apply space-y-3;
}

.transcript-item {
  @apply flex gap-4 p-4 bg-dark-800/30 border border-dark-700/50 rounded-2xl;
}

.speaker-avatar {
  @apply flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-sm font-medium text-white;
}

.transcript-content {
  @apply flex-1 min-w-0;
}

.transcript-header {
  @apply flex items-center gap-3 mb-1;
}

.speaker-name {
  @apply text-sm font-medium text-primary-400;
}

.transcript-time {
  @apply text-xs text-dark-500;
}

.transcript-text {
  @apply text-dark-200 leading-relaxed;
}

.not-found {
  @apply py-20 text-center;
}

.btn-primary {
  @apply px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white font-medium rounded-lg transition-colors;
}
</style>