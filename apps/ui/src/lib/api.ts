import axios from 'axios'
import { ChatRequest, ChatResponse } from '@/types/chat'
import { TaskRequest, TaskResponse, Task } from '@/types/task'
import { EnvironmentListResponse, EnvironmentResponse } from '@/types/environment'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Chat API
export const chatApi = {
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post('/api/v1/conversation/chat', request)
    return response.data
  },

  streamMessage: async (request: ChatRequest): Promise<ReadableStream> => {
    const response = await fetch(`${API_BASE_URL}/api/v1/conversation/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })
    
    if (!response.ok) {
      throw new Error('Stream request failed')
    }
    
    return response.body!
  },

  getSession: async (sessionId: string): Promise<any> => {
    const response = await api.get(`/api/v1/conversation/sessions/${sessionId}`)
    return response.data
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/api/v1/conversation/sessions/${sessionId}`)
  },
}

// Task API
export const taskApi = {
  createTask: async (request: TaskRequest): Promise<TaskResponse> => {
    const response = await api.post('/api/v1/tasks', request)
    return response.data
  },

  getTask: async (taskId: string): Promise<Task> => {
    const response = await api.get(`/api/v1/tasks/${taskId}`)
    return response.data
  },

  listTasks: async (limit = 50, offset = 0): Promise<{ tasks: Task[]; total: number }> => {
    const response = await api.get('/api/v1/tasks', {
      params: { limit, offset },
    })
    return response.data
  },

  approveTask: async (taskId: string, approved: boolean, reason?: string): Promise<void> => {
    await api.post(`/api/v1/tasks/${taskId}/approve`, {
      approved,
      reason,
    })
  },

  cancelTask: async (taskId: string): Promise<void> => {
    await api.delete(`/api/v1/tasks/${taskId}`)
  },
}

// Environment API
export const environmentApi = {
  listEnvironments: async (): Promise<EnvironmentListResponse> => {
    const response = await api.get('/api/v1/environments')
    return response.data
  },

  getEnvironment: async (environmentId: string): Promise<EnvironmentResponse> => {
    const response = await api.get(`/api/v1/environments/${environmentId}`)
    return response.data
  },

  validateEnvironment: async (environmentId: string): Promise<any> => {
    const response = await api.post(`/api/v1/environments/${environmentId}/validate`)
    return response.data
  },

  getEnvironmentRunbooks: async (environmentId: string): Promise<any> => {
    const response = await api.get(`/api/v1/environments/${environmentId}/runbooks`)
    return response.data
  },
}

// Health API
export const healthApi = {
  checkHealth: async (): Promise<any> => {
    const response = await api.get('/api/v1/health')
    return response.data
  },

  checkReadiness: async (): Promise<any> => {
    const response = await api.get('/api/v1/health/ready')
    return response.data
  },

  checkLiveness: async (): Promise<any> => {
    const response = await api.get('/api/v1/health/live')
    return response.data
  },

  getMetrics: async (): Promise<string> => {
    const response = await api.get('/api/v1/health/metrics')
    return response.data
  },
}

export default api




