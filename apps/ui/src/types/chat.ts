export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: {
    task_id?: string
    requires_approval?: boolean
    risk_level?: 'low' | 'medium' | 'high'
  }
}

export interface ChatRequest {
  message: string
  session_id?: string
  environment_profile?: string
  context?: Record<string, any>
  stream?: boolean
}

export interface ChatResponse {
  session_id: string
  message: string
  task_id?: string
  requires_approval?: boolean
  risk_level?: 'low' | 'medium' | 'high'
  metadata?: Record<string, any>
}






