<template>
  <div class="new-task-page">
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('newTaskTitle') }}</h1>
        <p class="page-subtitle">{{ t('newTaskSubtitle') }}</p>
      </div>
    </div>

    <!-- Upload grid -->
    <div class="upload-grid">
      <!-- Dropzone -->
      <div class="card upload-card">
        <div
          class="dropzone"
          :class="{ 'dropzone-active': isDragging, 'dropzone-disabled': uploading }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleDrop"
          @click="!uploading && fileInput?.click()"
        >
          <input
            ref="fileInput"
            type="file"
            :accept="acceptTypes"
            class="hidden"
            @change="handleFileSelect"
          />

          <div class="dropzone-icon">
            <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
            </svg>
          </div>

          <div class="dropzone-copy">
            <p class="dropzone-title">{{ uploadTitle }}</p>
            <p class="dropzone-body">{{ uploading && fileName ? fileName : t('uploadBody') }}</p>
            <p class="dropzone-hint">{{ t('uploadHint') }}</p>
          </div>

          <button type="button" class="btn-primary" :disabled="uploading">
            <svg v-if="!uploading" class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
            </svg>
            <svg v-else class="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            {{ uploading ? t('uploadingLabel') : t('chooseFile') }}
          </button>
        </div>
      </div>

      <!-- Settings -->
      <div class="card settings-card">
        <div class="settings-header">
          <h2 class="settings-title">{{ t('settingsLabel') }}</h2>
          <p class="settings-body">{{ t('settingsBody') }}</p>
        </div>

        <div class="settings-fields">
          <div class="field">
            <label class="field-label">{{ t('languageLabel') }}</label>
            <div class="choice-group">
              <button
                v-for="option in languageOptions"
                :key="`lang-${option.value}`"
                type="button"
                class="choice-chip"
                :class="{ 'choice-chip-active': language === option.value }"
                @click="language = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <div class="field">
            <label class="field-label">{{ t('speakerLabel') }}</label>
            <div class="choice-group">
              <button
                v-for="option in speakerOptions"
                :key="`speaker-${option.value || 'auto'}`"
                type="button"
                class="choice-chip"
                :class="{ 'choice-chip-active': speakerCount === option.value }"
                @click="speakerCount = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="error" class="error-note">
          {{ error }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '../stores/task'
import { useLocale } from '../composables/useLocale'

const router = useRouter()
const taskStore = useTaskStore()
const { t } = useLocale()

const fileInput = ref(null)
const isDragging = ref(false)
const fileName = ref('')
const uploading = ref(false)
const language = ref('auto')
const speakerCount = ref('')
const error = computed(() => taskStore.error)

const acceptTypes = '.mp3,.wav,.m4a,.webm,.ogg,.flac,.aac'

const languageOptions = computed(() => [
  { value: 'auto', label: t('languageAuto') },
  { value: 'zh', label: t('languageZh') },
  { value: 'en', label: t('languageEn') },
])

const speakerOptions = computed(() => [
  { value: '', label: t('speakerAuto') },
  { value: '2', label: t('speakerTwo') },
  { value: '3', label: t('speakerThree') },
  { value: '4', label: t('speakerFour') },
])

const uploadTitle = computed(() => {
  if (uploading.value) return t('uploadTitleUploading')
  if (isDragging.value) return t('uploadTitleDragging')
  return t('uploadTitleIdle')
})

function handleDrop(event) {
  isDragging.value = false
  const files = event.dataTransfer.files
  if (files.length > 0) processFile(files[0])
}

function handleFileSelect(event) {
  const files = event.target.files
  if (files.length > 0) processFile(files[0])
  event.target.value = ''
}

async function processFile(file) {
  fileName.value = file.name
  uploading.value = true

  try {
    const options = { language: language.value }
    if (speakerCount.value) {
      options.speaker_count = Number(speakerCount.value)
    }

    const task = await taskStore.createTask(file, options)
    if (task?.task_id) {
      router.push({ name: 'task-detail', params: { id: task.task_id } })
    }
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.new-task-page {
  @apply space-y-6;
}

/* ── Page header ── */
.page-header {
  @apply flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between;
}

.page-title {
  @apply text-2xl font-semibold tracking-tight;
  color: var(--text-strong);
}

.page-subtitle {
  @apply mt-1 text-sm;
  color: var(--muted);
}

/* ── Upload grid ── */
.upload-grid {
  @apply grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px];
}

.upload-card {
  @apply overflow-hidden;
}

/* ── Dropzone ── */
.dropzone {
  @apply flex min-h-[360px] cursor-pointer flex-col items-center justify-center gap-6 p-8 text-center transition-all duration-200;
  background: linear-gradient(180deg, #ffffff 0%, #f8f8fa 100%);
}

.dropzone-active {
  box-shadow: inset 0 0 0 2px rgba(0, 113, 227, 0.3);
  background: rgba(0, 113, 227, 0.02);
}

.dropzone-disabled {
  @apply cursor-progress opacity-75;
}

.dropzone-icon {
  @apply flex h-16 w-16 items-center justify-center rounded-2xl;
  background: rgba(0, 113, 227, 0.08);
  color: var(--accent);
}

.dropzone-copy {
  @apply max-w-md space-y-2;
}

.dropzone-title {
  @apply text-lg font-semibold;
  color: var(--text-strong);
}

.dropzone-body {
  @apply text-sm;
  color: var(--muted);
}

.dropzone-hint {
  @apply text-xs;
  color: var(--muted-subtle);
}

/* ── Settings ── */
.settings-card {
  @apply flex flex-col;
}

.settings-header {
  @apply border-b px-5 py-4;
  border-color: var(--line);
}

.settings-title {
  @apply text-base font-semibold;
  color: var(--text-strong);
}

.settings-body {
  @apply mt-1 text-sm;
  color: var(--muted);
}

.settings-fields {
  @apply flex flex-1 flex-col gap-5 px-5 py-5;
}

.field {
  @apply space-y-2;
}

.field-label {
  @apply block text-sm font-medium;
  color: var(--text-strong);
}

.choice-group {
  @apply flex flex-wrap gap-2;
}

.choice-chip {
  @apply inline-flex items-center justify-center rounded-lg border px-3 py-2 text-sm font-medium transition-colors duration-150;
  border-color: var(--line);
  background: white;
  color: var(--muted);
}

.choice-chip:hover {
  border-color: rgba(0, 113, 227, 0.2);
  color: var(--text-strong);
}

.choice-chip-active {
  border-color: var(--accent);
  background: rgba(0, 113, 227, 0.06);
  color: var(--accent);
}

.error-note {
  @apply mx-5 mb-5 rounded-lg px-4 py-3 text-sm;
  background: rgba(255, 59, 48, 0.06);
  color: var(--danger);
}
</style>
