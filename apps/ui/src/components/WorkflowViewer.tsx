'use client'

import { useState, useEffect } from 'react'
import { GitBranch, Clock, CheckCircle, XCircle, AlertCircle, ChevronRight, RefreshCw } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { Task } from '@/types/task'

interface WorkflowViewerProps {
  task: Task | null
}

interface WorkflowLog {
  task_id: string
  status: string
  workflow: any
  audit_logs: Array<{
    timestamp: string
    action: string
    details: any
    user_id?: string
  }>
  created_at: string
  updated_at: string
}

export function WorkflowViewer({ task }: WorkflowViewerProps) {
  const [workflowData, setWorkflowData] = useState<WorkflowLog | null>(null)
  const [loading, setLoading] = useState(false)
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (task?.task_id) {
      loadWorkflowData(task.task_id)
    }
  }, [task])

  const loadWorkflowData = async (taskId: string) => {
    setLoading(true)
    try {
      const data = await adminApi.getWorkflowLogs(taskId)
      setWorkflowData(data)
    } catch (error) {
      console.error('Failed to load workflow data:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleStep = (stepId: string) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev)
      if (newSet.has(stepId)) {
        newSet.delete(stepId)
      } else {
        newSet.add(stepId)
      }
      return newSet
    })
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      case 'in_progress':
        return <Clock className="h-5 w-5 text-blue-500 animate-pulse" />
      case 'pending':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />
      default:
        return <Clock className="h-5 w-5 text-gray-500" />
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleString('ru-RU')
  }

  if (!task) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <GitBranch className="h-16 w-16 mx-auto mb-4 text-gray-300" />
          <p className="text-gray-500">Выберите задачу для просмотра workflow</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <GitBranch className="h-6 w-6 text-gray-700" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Workflow Viewer</h1>
              <p className="text-sm text-gray-600">Task ID: {task.task_id}</p>
            </div>
          </div>
          <button
            onClick={() => loadWorkflowData(task.task_id)}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Обновить</span>
          </button>
        </div>

        {/* Task Status */}
        <div className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
          {getStatusIcon(workflowData?.status || task.status)}
          <div>
            <p className="font-medium">Статус: {workflowData?.status || task.status}</p>
            <p className="text-sm text-gray-600">
              Создано: {workflowData?.created_at ? formatTimestamp(workflowData.created_at) : 'N/A'}
            </p>
            {workflowData?.updated_at && (
              <p className="text-sm text-gray-600">
                Обновлено: {formatTimestamp(workflowData.updated_at)}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-6">
          {/* Workflow Steps */}
          {workflowData?.workflow && Object.keys(workflowData.workflow).length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Шаги Workflow</h2>
              <div className="space-y-3">
                {Object.entries(workflowData.workflow).map(([stepId, stepData]: [string, any]) => (
                  <div key={stepId} className="border rounded-lg">
                    <button
                      onClick={() => toggleStep(stepId)}
                      className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        {getStatusIcon(stepData.status || 'pending')}
                        <span className="font-medium">{stepId}</span>
                      </div>
                      <ChevronRight
                        className={`h-5 w-5 text-gray-400 transition-transform ${
                          expandedSteps.has(stepId) ? 'rotate-90' : ''
                        }`}
                      />
                    </button>
                    
                    {expandedSteps.has(stepId) && (
                      <div className="p-4 border-t bg-gray-50">
                        <pre className="text-xs text-gray-800 whitespace-pre-wrap overflow-auto">
                          {JSON.stringify(stepData, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Task Results */}
          {task.results && task.results.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Результаты выполнения</h2>
              <div className="space-y-3">
                {task.results.map((result, index) => (
                  <div key={index} className="p-4 border rounded-lg">
                    <div className="flex items-center space-x-3 mb-2">
                      {getStatusIcon(result.status)}
                      <div>
                        <p className="font-medium">{result.agent}</p>
                        <p className="text-sm text-gray-600">{result.message}</p>
                      </div>
                    </div>
                    
                    {result.error && (
                      <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
                        <p className="text-sm text-red-800">{result.error}</p>
                      </div>
                    )}

                    {result.metadata && (
                      <div className="mt-3">
                        <p className="text-xs text-gray-600 mb-2">Метаданные:</p>
                        <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto">
                          {JSON.stringify(result.metadata, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Audit Logs */}
          {workflowData?.audit_logs && workflowData.audit_logs.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Журнал аудита</h2>
              <div className="space-y-2">
                {workflowData.audit_logs.map((log, index) => (
                  <div key={index} className="p-4 border-l-4 border-blue-500 bg-gray-50 rounded">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="font-medium">{log.action}</p>
                        <p className="text-xs text-gray-600">
                          {formatTimestamp(log.timestamp)}
                        </p>
                      </div>
                      {log.user_id && (
                        <span className="text-xs text-gray-500">User: {log.user_id}</span>
                      )}
                    </div>
                    
                    {log.details && (
                      <pre className="text-xs text-gray-700 mt-2 whitespace-pre-wrap">
                        {typeof log.details === 'string' 
                          ? log.details 
                          : JSON.stringify(log.details, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Task Metadata */}
          {task.metadata && Object.keys(task.metadata).length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Метаданные задачи</h2>
              <pre className="text-xs text-gray-800 bg-gray-50 p-4 rounded overflow-auto">
                {JSON.stringify(task.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
