<template>
  <div class="card p-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-medium text-dark-100">处理进度</h3>
      <span :class="statusBadgeClass">{{ statusText }}</span>
    </div>

    <!-- Progress bar -->
    <div class="relative h-2 bg-dark-700 rounded-full overflow-hidden mb-4">
      <div
        class="absolute inset-y-0 left-0 bg-gradient-to-r from-primary-500 to-primary-400 transition-all duration-500 ease-out"
        :style="{ width: `${progress}%` }"
      ></div>
    </div>

    <!-- Stage info -->
    <div v-if="stage" class="flex items-center justify-between text-sm">
      <span class="text-dark-400">{{ stageDescription }}</span>
      <span class="text-dark-300 font-medium">{{ progress }}%</span>
    </div>

    <!-- Estimated time -->
    <div v-if="estimatedRemaining && status === 'processing'" class="mt-3 text-xs text-dark-500">
      预计剩余时间: {{ formatTime(estimatedRemaining) }}
    </div>

    <!-- Error message -->
    <div v-if="error" class="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
      <p class="text-sm text-red-400">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'pending',
  },
  progress: {
    type: Number,
    default: 0,
  },
  stage: {
    type: String,
    default: null,
  },
  stageDescription: {
    type: String,
    default: null,
  },
  estimatedRemaining: {
    type: Number,
    default: null,
  },
  error: {
    type: String,
    default: null,
  },
})

const statusText = computed(() => {
  const map = {
    pending: '等待中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
  }
  return map[props.status] || props.status
})

const statusBadgeClass = computed(() => {
  const map = {
    pending: 'badge badge-pending',
    processing: 'badge badge-processing',
    completed: 'badge badge-completed',
    failed: 'badge badge-failed',
  }
  return map[props.status] || 'badge'
})

function formatTime(seconds) {
  if (seconds < 60) return `${seconds} 秒`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (minutes < 60) return `${minutes} 分 ${secs} 秒`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours} 时 ${mins} 分`
}
</script>