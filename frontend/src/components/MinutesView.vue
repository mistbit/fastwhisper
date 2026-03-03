<template>
  <div class="space-y-6">
    <!-- Summary -->
    <div v-if="minutes.summary" class="card p-6">
      <h3 class="text-lg font-medium text-dark-100 mb-3 flex items-center">
        <svg class="w-5 h-5 text-primary-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        会议摘要
      </h3>
      <p class="text-dark-300 leading-relaxed">{{ minutes.summary }}</p>
    </div>

    <!-- Key Points -->
    <div v-if="minutes.key_points?.length" class="card p-6">
      <h3 class="text-lg font-medium text-dark-100 mb-4 flex items-center">
        <svg class="w-5 h-5 text-yellow-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        关键要点
      </h3>
      <div class="space-y-3">
        <div
          v-for="(point, index) in minutes.key_points"
          :key="index"
          class="flex items-start space-x-3 p-3 bg-dark-700/30 rounded-lg"
        >
          <span class="flex-shrink-0 w-6 h-6 rounded-full bg-yellow-500/20 text-yellow-400 flex items-center justify-center text-xs font-medium">
            {{ index + 1 }}
          </span>
          <div>
            <h4 class="font-medium text-dark-100">{{ point.title }}</h4>
            <p class="text-sm text-dark-400 mt-1">{{ point.content }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Action Items -->
    <div v-if="minutes.action_items?.length" class="card p-6">
      <h3 class="text-lg font-medium text-dark-100 mb-4 flex items-center">
        <svg class="w-5 h-5 text-emerald-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
        </svg>
        待办事项
      </h3>
      <div class="space-y-2">
        <div
          v-for="(item, index) in minutes.action_items"
          :key="index"
          class="flex items-center justify-between p-3 bg-dark-700/30 rounded-lg"
        >
          <div class="flex items-center space-x-3">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span class="text-dark-200">{{ item.task }}</span>
          </div>
          <div class="flex items-center space-x-3 text-sm">
            <span v-if="item.assignee" class="text-primary-400">{{ item.assignee }}</span>
            <span v-if="item.deadline" class="text-dark-400">{{ item.deadline }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Decisions -->
    <div v-if="minutes.decisions?.length" class="card p-6">
      <h3 class="text-lg font-medium text-dark-100 mb-4 flex items-center">
        <svg class="w-5 h-5 text-purple-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        会议决策
      </h3>
      <div class="space-y-3">
        <div
          v-for="(decision, index) in minutes.decisions"
          :key="index"
          class="p-4 bg-purple-500/5 border border-purple-500/20 rounded-lg"
        >
          <h4 class="text-sm font-medium text-purple-400 mb-1">{{ decision.topic }}</h4>
          <p class="text-dark-200">{{ decision.decision }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  minutes: {
    type: Object,
    default: () => ({}),
  },
})
</script>