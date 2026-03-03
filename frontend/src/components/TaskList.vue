<template>
  <div class="card overflow-hidden">
    <!-- Header -->
    <div class="px-6 py-4 border-b border-dark-700/50 flex items-center justify-between">
      <h3 class="text-lg font-medium text-dark-100">任务列表</h3>

      <!-- Status filter -->
      <div class="flex items-center space-x-2">
        <select
          v-model="localStatus"
          class="input text-sm py-1.5"
          @change="$emit('filter', localStatus)"
        >
          <option value="">全部状态</option>
          <option value="pending">等待中</option>
          <option value="processing">处理中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading && tasks.length === 0" class="p-8 text-center">
      <div class="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full mx-auto"></div>
      <p class="mt-4 text-dark-400">加载中...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="tasks.length === 0" class="p-8 text-center">
      <svg class="w-12 h-12 text-dark-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
      <p class="text-dark-400">暂无任务</p>
    </div>

    <!-- Task list -->
    <div v-else class="divide-y divide-dark-700/50">
      <div
        v-for="task in tasks"
        :key="task.task_id"
        class="px-6 py-4 hover:bg-dark-700/30 transition-colors cursor-pointer group"
        @click="$emit('select', task)"
      >
        <div class="flex items-center justify-between">
          <div class="flex-1 min-w-0">
            <div class="flex items-center space-x-3">
              <span class="text-dark-100 font-medium truncate">{{ task.filename }}</span>
              <span :class="getStatusBadgeClass(task.status)">{{ getStatusText(task.status) }}</span>
            </div>
            <div class="mt-1 flex items-center space-x-4 text-sm text-dark-400">
              <span>{{ formatDate(task.created_at) }}</span>
              <span v-if="task.progress > 0 && task.progress < 100">{{ task.progress }}%</span>
            </div>
          </div>

          <!-- Progress bar for processing -->
          <div v-if="task.status === 'processing'" class="w-24 h-1.5 bg-dark-700 rounded-full overflow-hidden mr-4">
            <div
              class="h-full bg-primary-500 transition-all duration-300"
              :style="{ width: `${task.progress}%` }"
            ></div>
          </div>

          <!-- Delete button -->
          <button
            class="p-2 text-dark-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
            @click.stop="$emit('delete', task.task_id)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > pageSize" class="px-6 py-4 border-t border-dark-700/50 flex items-center justify-between">
      <span class="text-sm text-dark-400">共 {{ total }} 条记录</span>
      <div class="flex items-center space-x-2">
        <button
          class="btn-secondary text-sm py-1.5 px-3"
          :disabled="page <= 1"
          @click="$emit('page-change', page - 1)"
        >
          上一页
        </button>
        <span class="text-sm text-dark-400">{{ page }} / {{ totalPages }}</span>
        <button
          class="btn-secondary text-sm py-1.5 px-3"
          :disabled="page >= totalPages"
          @click="$emit('page-change', page + 1)"
        >
          下一页
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  tasks: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  total: {
    type: Number,
    default: 0,
  },
  page: {
    type: Number,
    default: 1,
  },
  pageSize: {
    type: Number,
    default: 20,
  },
  statusFilter: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['select', 'delete', 'filter', 'page-change'])

const localStatus = ref(props.statusFilter)

watch(() => props.statusFilter, (val) => {
  localStatus.value = val
})

const totalPages = computed(() => Math.ceil(props.total / props.pageSize))

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
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>