import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskApi } from '../api'

export const useTaskStore = defineStore('task', () => {
  // State
  const tasks = ref([])
  const currentTask = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const statusFilter = ref('')
  const progressInterval = ref(null)

  // Cleanup function
  function _cleanup() {
    stopProgressPolling()
  }

  // Actions
  async function createTask(file, options = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await taskApi.create(file, options)
      if (response.code === 201 && response.data) {
        tasks.value.unshift(response.data)
        return response.data
      }
      throw new Error(response.message || '创建任务失败')
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchTasks(params = {}) {
    loading.value = true
    error.value = null
    try {
      const queryParams = {
        page: params.page || page.value,
        page_size: params.pageSize || pageSize.value,
      }
      if (params.status || statusFilter.value) {
        queryParams.status = params.status || statusFilter.value
      }

      const response = await taskApi.list(queryParams)
      if (response.code === 200 && response.data) {
        tasks.value = response.data.items
        total.value = response.data.total
        page.value = response.data.page
        pageSize.value = response.data.page_size
      }
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchProgress(taskId) {
    try {
      const response = await taskApi.getProgress(taskId)
      if (response.code === 200 && response.data) {
        const index = tasks.value.findIndex(t => t.task_id === taskId)
        if (index !== -1) {
          tasks.value[index] = { ...tasks.value[index], ...response.data }
        }
        if (currentTask.value?.task_id === taskId) {
          currentTask.value = { ...currentTask.value, ...response.data }
        }
        return response.data
      }
    } catch (e) {
      console.error('Failed to fetch progress:', e)
    }
  }

  async function fetchMinutes(taskId) {
    loading.value = true
    error.value = null
    try {
      const response = await taskApi.getMinutes(taskId)
      if (response.code === 200 && response.data) {
        return response.data
      }
      throw new Error(response.message || '获取会议纪要失败')
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteTask(taskId) {
    try {
      const response = await taskApi.delete(taskId)
      if (response.code === 200) {
        tasks.value = tasks.value.filter(t => t.task_id !== taskId)
        return true
      }
      return false
    } catch (e) {
      error.value = e.message
      return false
    }
  }

  function setCurrentTask(task) {
    currentTask.value = task
  }

  function startProgressPolling(taskId, intervalMs = 2000) {
    stopProgressPolling()
    progressInterval.value = setInterval(() => {
      fetchProgress(taskId).then(progress => {
        if (progress && (progress.status === 'completed' || progress.status === 'failed')) {
          stopProgressPolling()
        }
      })
    }, intervalMs)
  }

  function stopProgressPolling() {
    if (progressInterval.value) {
      clearInterval(progressInterval.value)
      progressInterval.value = null
    }
  }

  // Computed
  const hasMore = computed(() => tasks.value.length < total.value)

  return {
    // State
    tasks,
    currentTask,
    loading,
    error,
    total,
    page,
    pageSize,
    statusFilter,
    // Actions
    createTask,
    fetchTasks,
    fetchProgress,
    fetchMinutes,
    deleteTask,
    setCurrentTask,
    startProgressPolling,
    stopProgressPolling,
    // Computed
    hasMore,
  }
})