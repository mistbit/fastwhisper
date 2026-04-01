import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { taskApi } from '../api'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const currentTask = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const stats = ref({
    total: 0,
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
    retried: 0,
    avg_queue_seconds: null,
    avg_processing_seconds: null,
    failure_breakdown: [],
  })
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const statusFilter = ref('')
  const progressInterval = ref(null)

  function syncTask(taskData) {
    if (!taskData?.task_id) return null

    const index = tasks.value.findIndex((task) => task.task_id === taskData.task_id)
    if (index === -1) {
      tasks.value.unshift(taskData)
    } else {
      tasks.value[index] = { ...tasks.value[index], ...taskData }
    }

    if (currentTask.value?.task_id === taskData.task_id) {
      currentTask.value = { ...currentTask.value, ...taskData }
    }

    return tasks.value.find((task) => task.task_id === taskData.task_id) || null
  }

  async function createTask(file, options = {}) {
    loading.value = true
    error.value = null

    try {
      const response = await taskApi.create(file, options)
      if (!response?.data) {
        throw new Error(response?.message || '创建任务失败')
      }

      const task = syncTask(response.data)
      total.value += 1
      currentTask.value = task
      await fetchOverview()
      return task
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

      const filter = params.status ?? statusFilter.value
      if (filter) {
        queryParams.status = filter
      }

      const response = await taskApi.list(queryParams)
      if (!response?.data) {
        return
      }

      tasks.value = response.data.items
      total.value = response.data.total
      page.value = response.data.page
      pageSize.value = response.data.page_size
      statusFilter.value = filter || ''
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(taskId) {
    loading.value = true
    error.value = null

    try {
      const response = await taskApi.getTask(taskId)
      if (!response?.data) {
        throw new Error(response?.message || '获取任务详情失败')
      }

      const existing = tasks.value.find((task) => task.task_id === taskId)
      const mergedTask = { ...existing, ...response.data }
      currentTask.value = mergedTask
      syncTask(mergedTask)
      return mergedTask
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchOverview() {
    try {
      const response = await taskApi.getOverview()
      if (!response?.data) {
        return null
      }

      stats.value = response.data
      return response.data
    } catch (e) {
      error.value = e.message
      return null
    }
  }

  async function fetchProgress(taskId) {
    try {
      const response = await taskApi.getProgress(taskId)
      if (!response?.data) {
        return null
      }

      const mergedTask = {
        ...(tasks.value.find((task) => task.task_id === taskId) || currentTask.value || {}),
        ...response.data,
      }
      syncTask(mergedTask)
      if (currentTask.value?.task_id === taskId) {
        currentTask.value = mergedTask
      }
      return mergedTask
    } catch (e) {
      error.value = e.message
      return null
    }
  }

  async function fetchMinutes(taskId) {
    loading.value = true
    error.value = null

    try {
      const response = await taskApi.getMinutes(taskId)
      if (!response?.data) {
        throw new Error(response?.message || '获取会议纪要失败')
      }
      return response.data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function retryTask(taskId) {
    error.value = null

    try {
      const response = await taskApi.retry(taskId)
      if (!response?.data) {
        throw new Error(response?.message || '重试任务失败')
      }

      const task = syncTask(response.data)
      currentTask.value = task
      await fetchOverview()
      return task
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  async function deleteTask(taskId) {
    error.value = null

    try {
      const response = await taskApi.delete(taskId)
      if (response?.code !== 200) {
        return false
      }

      tasks.value = tasks.value.filter((task) => task.task_id !== taskId)
      if (currentTask.value?.task_id === taskId) {
        currentTask.value = null
      }
      total.value = Math.max(0, total.value - 1)
      await fetchOverview()
      return true
    } catch (e) {
      error.value = e.message
      return false
    }
  }

  function setCurrentTask(task) {
    currentTask.value = task
  }

  function clearCurrentTask() {
    currentTask.value = null
  }

  function startProgressPolling(taskId, intervalMs = 2000) {
    stopProgressPolling()
    fetchProgress(taskId)
    progressInterval.value = window.setInterval(async () => {
      const task = await fetchProgress(taskId)
      if (task && ['completed', 'failed'].includes(task.status)) {
        stopProgressPolling()
      }
    }, intervalMs)
  }

  function stopProgressPolling() {
    if (progressInterval.value) {
      window.clearInterval(progressInterval.value)
      progressInterval.value = null
    }
  }

  const hasMore = computed(() => tasks.value.length < total.value)

  return {
    tasks,
    currentTask,
    loading,
    error,
    stats,
    total,
    page,
    pageSize,
    statusFilter,
    createTask,
    fetchTasks,
    fetchTask,
    fetchOverview,
    fetchProgress,
    fetchMinutes,
    retryTask,
    deleteTask,
    setCurrentTask,
    clearCurrentTask,
    startProgressPolling,
    stopProgressPolling,
    syncTask,
    hasMore,
  }
})
