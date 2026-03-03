<template>
  <div class="space-y-6">
    <!-- Back button -->
    <button
      @click="router.back()"
      class="flex items-center text-dark-400 hover:text-dark-200 transition-colors"
    >
      <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      返回列表
    </button>

    <!-- Loading state -->
    <div v-if="loading" class="card p-8 text-center">
      <div class="animate-spin w-10 h-10 border-2 border-primary-500 border-t-transparent rounded-full mx-auto"></div>
      <p class="mt-4 text-dark-400">加载中...</p>
    </div>

    <!-- Task content -->
    <div v-else-if="task" class="space-y-6">
      <!-- Task header -->
      <div class="card p-6">
        <div class="flex items-start justify-between">
          <div>
            <h1 class="text-xl font-semibold text-dark-100">{{ task.filename }}</h1>
            <p class="text-sm text-dark-400 mt-1">
              创建于 {{ formatDate(task.created_at) }}
            </p>
          </div>
          <span :class="getStatusBadgeClass(task.status)">{{ getStatusText(task.status) }}</span>
        </div>
      </div>

      <!-- Progress -->
      <ProgressCard
        :status="task.status"
        :progress="task.progress"
        :stage="task.stage"
        :stage-description="task.stage_description"
        :estimated-remaining="task.estimated_remaining"
        :error="task.error_message"
      />

      <!-- Results (only show when completed) -->
      <template v-if="task.status === 'completed' && minutes">
        <!-- Tabs -->
        <div class="flex space-x-1 p-1 bg-dark-800/50 rounded-lg w-fit">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="px-4 py-2 text-sm font-medium rounded-md transition-colors"
            :class="activeTab === tab.id ? 'bg-dark-700 text-dark-100' : 'text-dark-400 hover:text-dark-200'"
            @click="activeTab = tab.id"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- Minutes tab -->
        <div v-show="activeTab === 'minutes'">
          <MinutesView :minutes="minutes.minutes" />
        </div>

        <!-- Transcript tab -->
        <div v-show="activeTab === 'transcript'">
          <TranscriptView :segments="minutes.transcript.segments" />
        </div>
      </template>

      <!-- Waiting/Processing state -->
      <div v-else-if="task.status === 'pending' || task.status === 'processing'" class="card p-8 text-center">
        <div class="animate-pulse-slow">
          <svg class="w-16 h-16 text-primary-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        </div>
        <p class="text-dark-300">正在处理中，请稍候...</p>
        <p class="text-sm text-dark-500 mt-2">处理时间取决于音频长度</p>
      </div>
    </div>

    <!-- Error state -->
    <div v-else class="card p-8 text-center">
      <p class="text-dark-400">任务不存在</p>
      <button @click="router.push('/')" class="btn-primary mt-4">返回首页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTaskStore } from '../stores/task'
import ProgressCard from '../components/ProgressCard.vue'
import MinutesView from '../components/MinutesView.vue'
import TranscriptView from '../components/TranscriptView.vue'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()

const loading = ref(true)
const task = ref(null)
const minutes = ref(null)
const activeTab = ref('minutes')

const tabs = [
  { id: 'minutes', label: '会议纪要' },
  { id: 'transcript', label: '转录文本' },
]

const taskId = route.params.id

// Watch for task updates from store
watch(
  () => taskStore.tasks.find(t => t.task_id === taskId),
  (updated) => {
    if (updated && task.value) {
      task.value = updated
    }
  }
)

onMounted(async () => {
  await loadTask()
})

onUnmounted(() => {
  taskStore.stopProgressPolling()
})

watch(() => task.value?.status, async (newStatus, oldStatus) => {
  if (newStatus === 'completed' && oldStatus !== 'completed') {
    await loadMinutes()
  }
})

async function loadTask() {
  loading.value = true
  try {
    let foundTask = taskStore.tasks.find(t => t.task_id === taskId)

    if (!foundTask) {
      const progress = await taskStore.fetchProgress(taskId)
      if (progress) {
        foundTask = progress
      }
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
    const result = await taskStore.fetchMinutes(taskId)
    minutes.value = result
  } catch (e) {
    console.error('Failed to load minutes:', e)
  }
}

function getStatusText(status) {
  const map = {
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

function getStatusBadgeClass(status) {
  const map = {
    pending: 'badge badge-pending',
    processing: 'badge badge-processing',
    completed: 'badge badge-completed',
    failed: 'badge badge-failed',
  }
  return map[status] || 'badge'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}
</script>