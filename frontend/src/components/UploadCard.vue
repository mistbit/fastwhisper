<template>
  <div
    class="card p-8"
    :class="{ 'border-primary-500/50 border-dashed': isDragging }"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="handleDrop"
  >
    <div v-if="!uploading" class="text-center">
      <!-- Upload icon -->
      <div class="mx-auto w-16 h-16 rounded-full bg-dark-700/50 flex items-center justify-center mb-4">
        <svg class="w-8 h-8 text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      </div>

      <h3 class="text-lg font-medium text-dark-100 mb-2">上传音频文件</h3>
      <p class="text-sm text-dark-400 mb-4">拖拽文件到此处，或点击选择文件</p>

      <!-- File input -->
      <input
        ref="fileInput"
        type="file"
        :accept="acceptTypes"
        class="hidden"
        @change="handleFileSelect"
      />
      <button @click="$refs.fileInput.click()" class="btn-primary">
        选择文件
      </button>

      <p class="mt-4 text-xs text-dark-500">
        支持 MP3, WAV, M4A, WEBM, OGG, FLAC, AAC 格式，最大 500MB
      </p>
    </div>

    <!-- Uploading state -->
    <div v-else class="text-center py-4">
      <div class="animate-spin w-10 h-10 border-2 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
      <p class="text-dark-300">正在上传...</p>
      <p v-if="fileName" class="text-sm text-dark-400 mt-1">{{ fileName }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  uploading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['upload'])

const fileInput = ref(null)
const isDragging = ref(false)
const fileName = ref('')

const acceptTypes = '.mp3,.wav,.m4a,.webm,.ogg,.flac,.aac'

function handleDrop(e) {
  isDragging.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) {
    processFile(files[0])
  }
}

function handleFileSelect(e) {
  const files = e.target.files
  if (files.length > 0) {
    processFile(files[0])
  }
}

function processFile(file) {
  fileName.value = file.name
  emit('upload', file)
}
</script>