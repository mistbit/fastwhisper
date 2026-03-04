<template>
  <div class="min-h-screen">
    <!-- Hero Section -->
    <div class="pt-12 pb-8 text-center">
      <h1 class="text-3xl font-semibold text-dark-100 tracking-tight">
        录音转会议纪要
      </h1>
      <p class="mt-2 text-dark-400">
        上传音频，智能转录并生成结构化会议纪要
      </p>
    </div>

    <!-- Upload Area -->
    <div
      class="upload-zone group"
      :class="{ 'upload-zone-active': isDragging, 'upload-zone-disabled': uploading }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      @click="!uploading && $refs.fileInput.click()"
    >
      <input
        ref="fileInput"
        type="file"
        :accept="acceptTypes"
        class="hidden"
        @change="handleFileSelect"
      />

      <!-- Idle State -->
      <div v-if="!uploading" class="upload-content">
        <div class="upload-icon">
          <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <p class="mt-4 text-lg font-medium text-dark-200">
          {{ isDragging ? '释放以上传' : '拖拽音频文件到此处' }}
        </p>
        <p class="mt-1 text-sm text-dark-500">
          或点击选择文件
        </p>
        <p class="mt-4 text-xs text-dark-600">
          MP3, WAV, M4A, WEBM, OGG, FLAC, AAC · 最大 500MB
        </p>
      </div>

      <!-- Uploading State -->
      <div v-else class="upload-content">
        <div class="upload-spinner">
          <svg class="animate-spin w-8 h-8" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <p class="mt-4 text-lg font-medium text-dark-200">正在上传</p>
        <p v-if="fileName" class="mt-1 text-sm text-dark-500">{{ fileName }}</p>
      </div>
    </div>

    <!-- Task List -->
    <div class="mt-10">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-sm font-medium text-dark-400 uppercase tracking-wider">
          历史记录
        </h2>
        <select
          v-model="localStatus"
          class="filter-select"
          @change="$emit('filter', localStatus)"
        >
          <option value="">全部</option>
          <option value="processing">处理中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>
      </div>

      <!-- Loading -->
      <div v-if="loading && tasks.length === 0" class="loading-state">
        <div class="loading-spinner"></div>
      </div>

      <!-- Empty State -->
      <div v-else-if="tasks.length === 0" class="empty-state">
        <svg class="w-12 h-12 text-dark-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
        <p class="mt-3 text-dark-500">暂无录音记录</p>
      </div>

      <!-- Task Grid -->
      <div v-else class="task-grid">
        <div
          v-for="task in tasks"
          :key="task.task_id"
          class="task-card group"
          @click="$emit('select', task)"
        >
          <!-- Status Indicator -->
          <div class="task-status" :class="`status-${task.status}`"></div>

          <!-- Content -->
          <div class="task-content">
            <div class="task-header">
              <h3 class="task-title">{{ task.filename }}</h3>
              <span class="task-badge" :class="`badge-${task.status}`">
                {{ getStatusText(task.status) }}
              </span>
            </div>

            <div class="task-meta">
              <span>{{ formatDate(task.created_at) }}</span>
              <span v-if="task.status === 'processing'" class="text-primary-400">
                {{ task.progress }}%
              </span>
            </div>

            <!-- Progress Bar -->
            <div v-if="task.status === 'processing'" class="task-progress">
              <div class="progress-bar" :style="{ width: `${task.progress}%` }"></div>
            </div>
          </div>

          <!-- Delete Button -->
          <button
            class="task-delete"
            @click.stop="$emit('delete', task.task_id)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="total > pageSize" class="pagination">
        <span class="text-sm text-dark-500">共 {{ total }} 条</span>
        <div class="pagination-buttons">
          <button
            class="page-btn"
            :disabled="page <= 1"
            @click="$emit('page-change', page - 1)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span class="page-info">{{ page }} / {{ totalPages }}</span>
          <button
            class="page-btn"
            :disabled="page >= totalPages"
            @click="$emit('page-change', page + 1)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  uploading: Boolean,
  tasks: { type: Array, default: () => [] },
  loading: Boolean,
  total: { type: Number, default: 0 },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
  statusFilter: { type: String, default: '' },
})

const emit = defineEmits(['upload', 'select', 'delete', 'filter', 'page-change'])

const fileInput = ref(null)
const isDragging = ref(false)
const localStatus = ref(props.statusFilter)
const fileName = ref('')

const acceptTypes = '.mp3,.wav,.m4a,.webm,.ogg,.flac,.aac'

watch(() => props.statusFilter, (val) => {
  localStatus.value = val
})

const totalPages = computed(() => Math.ceil(props.total / props.pageSize))

function handleDrop(e) {
  isDragging.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) processFile(files[0])
}

function handleFileSelect(e) {
  const files = e.target.files
  if (files.length > 0) processFile(files[0])
}

function processFile(file) {
  fileName.value = file.name
  emit('upload', file)
}

function getStatusText(status) {
  return { pending: '等待', processing: '处理中', completed: '已完成', failed: '失败' }[status] || status
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.upload-zone {
  @apply relative border-2 border-dashed border-dark-700 rounded-2xl p-12 transition-all duration-300 cursor-pointer;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.02) 0%, rgba(14, 165, 233, 0.05) 100%);
}

.upload-zone:hover {
  @apply border-dark-600;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.03) 0%, rgba(14, 165, 233, 0.08) 100%);
}

.upload-zone-active {
  @apply border-primary-500 bg-primary-500/5;
}

.upload-zone-disabled {
  @apply cursor-not-allowed opacity-75;
}

.upload-icon {
  @apply w-16 h-16 mx-auto rounded-2xl bg-dark-800/80 flex items-center justify-center text-dark-400;
}

.upload-spinner {
  @apply w-16 h-16 mx-auto rounded-2xl bg-primary-500/10 flex items-center justify-center text-primary-400;
}

.filter-select {
  @apply px-3 py-1.5 bg-dark-800/50 border border-dark-700 rounded-lg text-sm text-dark-300 focus:outline-none focus:border-dark-600;
}

.loading-state {
  @apply py-16 text-center;
}

.loading-spinner {
  @apply w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto;
}

.empty-state {
  @apply py-16 text-center;
}

.task-grid {
  @apply grid gap-3;
}

.task-card {
  @apply relative flex items-center p-4 bg-dark-800/30 border border-dark-700/50 rounded-xl cursor-pointer transition-all duration-200;
}

.task-card:hover {
  @apply bg-dark-800/50 border-dark-600/50;
}

.task-status {
  @apply absolute left-0 top-4 bottom-4 w-1 rounded-full;
}

.status-pending { @apply bg-yellow-500/50; }
.status-processing { @apply bg-primary-500 animate-pulse; }
.status-completed { @apply bg-emerald-500/50; }
.status-failed { @apply bg-red-500/50; }

.task-content {
  @apply flex-1 min-w-0 pl-3;
}

.task-header {
  @apply flex items-center gap-3;
}

.task-title {
  @apply text-dark-100 font-medium truncate;
}

.task-badge {
  @apply flex-shrink-0 px-2 py-0.5 rounded text-xs font-medium;
}

.badge-pending { @apply bg-yellow-500/10 text-yellow-400; }
.badge-processing { @apply bg-primary-500/10 text-primary-400; }
.badge-completed { @apply bg-emerald-500/10 text-emerald-400; }
.badge-failed { @apply bg-red-500/10 text-red-400; }

.task-meta {
  @apply flex items-center gap-4 mt-1 text-sm text-dark-500;
}

.task-progress {
  @apply mt-3 h-1 bg-dark-700 rounded-full overflow-hidden;
}

.progress-bar {
  @apply h-full bg-gradient-to-r from-primary-500 to-primary-400 transition-all duration-500;
}

.task-delete {
  @apply p-2 text-dark-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all;
}

.pagination {
  @apply flex items-center justify-between mt-6 pt-6 border-t border-dark-800;
}

.pagination-buttons {
  @apply flex items-center gap-2;
}

.page-btn {
  @apply p-1.5 rounded-lg text-dark-400 hover:text-dark-200 hover:bg-dark-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors;
}

.page-info {
  @apply text-sm text-dark-400 px-2;
}
</style>