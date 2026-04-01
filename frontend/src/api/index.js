import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 30000,
})

// Request interceptor - add auth token
api.interceptors.request.use((config) => {
  const token = import.meta.env.VITE_API_TOKEN
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    const wrapped = new Error(message)
    wrapped.status = error.response?.status
    return Promise.reject(wrapped)
  }
)

// Task API
export const taskApi = {
  // Create task with audio file
  create(file, options = {}) {
    const formData = new FormData()
    formData.append('file', file)
    if (options.language) formData.append('language', options.language)
    if (options.speaker_count) formData.append('speaker_count', options.speaker_count)
    return api.post('/api/v1/tasks', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // Get task detail
  getTask(taskId) {
    return api.get(`/api/v1/tasks/${taskId}`)
  },

  // Get task progress
  getProgress(taskId) {
    return api.get(`/api/v1/tasks/${taskId}/progress`)
  },

  // Retry failed task
  retry(taskId) {
    return api.post(`/api/v1/tasks/${taskId}/retry`)
  },

  // Get task overview stats
  getOverview() {
    return api.get('/api/v1/tasks/stats/overview')
  },

  // Get meeting minutes
  getMinutes(taskId) {
    return api.get(`/api/v1/tasks/${taskId}/minutes`)
  },

  // Get task list
  list(params = {}) {
    return api.get('/api/v1/tasks', { params })
  },

  // Delete task
  delete(taskId) {
    return api.delete(`/api/v1/tasks/${taskId}`)
  },
}

// Health check
export const healthCheck = () => api.get('/health')

export default api
