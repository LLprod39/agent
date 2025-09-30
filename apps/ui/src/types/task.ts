export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'

export interface TaskStep {
  id: string
  description: string
  command?: string
  tool?: string
  parameters?: Record<string, any>
  risk_level: 'low' | 'medium' | 'high'
  requires_approval: boolean
  dependencies?: string[]
}

export interface Task {
  task_id: string
  status: TaskStatus
  current_step: string
  results: TaskResult[]
  error?: string
  metadata?: Record<string, any>
  created_at?: string
  updated_at?: string
}

export interface TaskResult {
  agent: string
  status: TaskStatus
  message: string
  step_id?: string
  metadata?: Record<string, any>
  error?: string
}

export interface TaskRequest {
  task: string
  environment_profile?: string
  context?: Record<string, any>
  auto_approve?: boolean
  metadata?: Record<string, any>
}

export interface TaskResponse {
  task_id: string
  status: TaskStatus
  message: string
  results: TaskResult[]
  requires_approval?: boolean
  risk_level?: 'low' | 'medium' | 'high'
  metadata?: Record<string, any>
}




