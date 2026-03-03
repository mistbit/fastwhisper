<template>
  <div class="space-y-8">
    <!-- Upload Section -->
    <section>
      <h2 class="text-xl font-semibold text-dark-100 mb-4">上传音频</h2>
      <UploadCard :uploading="uploading" @upload="handleUpload" />
    </section>

    <!-- Tasks Section -->
    <section>
      <h2 class="text-xl font-semibold text-dark-100 mb-4">任务列表</h2>
      <TaskList
        :tasks="taskStore.tasks"
        :loading="taskStore.loading"
        :total="taskStore.total"
        :page="taskStore.page"
        :page-size="taskStore.pageSize"
        :status-filter="taskStore.statusFilter"
        @select="handleSelectTask"
        @delete="handleDeleteTask"
        @filter="handleFilter"
        @page-change="handlePageChange"
      />
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '../stores/task'
import UploadCard from '../components/UploadCard.vue'
import TaskList from '../components/TaskList.vue'

const router = useRouter()
const taskStore = useTaskStore()

const uploading = ref(false)

onMounted(() => {
  taskStore.fetchTasks()
})

async function handleUpload(file) {
  uploading.value = true
  try {
    const task = await taskStore.createTask(file, { language: 'auto' })
    router.push({ name: 'task-detail', params: { id: task.task_id } })
  } catch (e) {
    alert(e.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

function handleSelectTask(task) {
  router.push({ name: 'task-detail', params: { id: task.task_id } })
}

async function handleDeleteTask(taskId) {
  if (confirm('确定要删除这个任务吗？')) {
    await taskStore.deleteTask(taskId)
  }
}

function handleFilter(status) {
  taskStore.statusFilter = status
  taskStore.fetchTasks({ status })
}

function handlePageChange(page) {
  taskStore.fetchTasks({ page })
}
</script>