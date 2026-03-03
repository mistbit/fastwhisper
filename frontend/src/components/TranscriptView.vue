<template>
  <div class="space-y-4">
    <div
      v-for="(segment, index) in segments"
      :key="index"
      class="card p-4 hover:border-dark-600/50 transition-colors"
    >
      <div class="flex items-start space-x-4">
        <!-- Speaker badge -->
        <div class="flex-shrink-0">
          <div class="w-10 h-10 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center">
            <span class="text-sm font-medium text-white">{{ getSpeakerInitial(segment.speaker_label || segment.speaker) }}</span>
          </div>
        </div>

        <!-- Content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center space-x-2 mb-1">
            <span class="text-sm font-medium text-primary-400">{{ segment.speaker_label || segment.speaker }}</span>
            <span class="text-xs text-dark-500">{{ formatTime(segment.start_time) }} - {{ formatTime(segment.end_time) }}</span>
          </div>
          <p class="text-dark-200 leading-relaxed">{{ segment.text }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  segments: {
    type: Array,
    default: () => [],
  },
})

function getSpeakerInitial(speaker) {
  if (!speaker) return '?'
  // Extract number from SPEAKER_01 or use first two chars
  const match = speaker.match(/(\d+)/)
  if (match) return match[1]
  return speaker.slice(0, 2).toUpperCase()
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
</script>