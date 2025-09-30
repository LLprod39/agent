'use client'

import { useState, useEffect } from 'react'
import { Clock, CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react'
import { Task } from '@/types/task'
import { taskApi } from '@/lib/api'

interface TaskMonitorProps {
  tasks: Task[]
  onTaskUpdate: () => void
}

export function TaskMonitor({ tasks, onTaskUpdate }: TaskMonitorProps) {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      onTaskUpdate()
    }, 3000)

    return () => clearInterval(interval)
  }, [autoRefresh, onTaskUpdate])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'in_progress':
        return <Clock className="h-4 w-4 text-blue-500 animate-pulse" />
      case 'pending':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'in_progress':
        return 'bg-blue-100 text-blue-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const handleApproveTask = async (taskId: string, approved: boolean) => {
    try {
      await taskApi.approveTask(taskId, approved)
      onTaskUpdate()
    } catch (error) {
      console.error('Failed to approve task:', error)
    }
  }

  const handleCancelTask = async (taskId: string) => {
    try {
      await taskApi.cancelTask(taskId)
      onTaskUpdate()
    } catch (error) {
      console.error('Failed to cancel task:', error)
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b bg-white">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Task Monitor</h2>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`p-1 rounded ${autoRefresh ? 'text-blue-500' : 'text-gray-400'}`}
              title={autoRefresh ? 'Auto-refresh enabled' : 'Auto-refresh disabled'}
            >
              <RefreshCw className={`h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onTaskUpdate}
              className="p-1 text-gray-400 hover:text-gray-600"
              title="Refresh now"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto p-4">
        {tasks.length === 0 ? (
          <div className="text-center py-8">
            <Clock className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500">No active tasks</p>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <div
                key={task.task_id}
                className={`p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
                  selectedTask?.task_id === task.task_id ? 'ring-2 ring-blue-500 bg-blue-50' : ''
                }`}
                onClick={() => setSelectedTask(task)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(task.status)}
                    <span className="font-medium text-sm">
                      {task.task_id.slice(0, 8)}...
                    </span>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
                    {task.status}
                  </span>
                </div>
                
                <div className="text-sm text-gray-600">
                  {task.current_step}
                </div>
                
                {task.error && (
                  <div className="text-sm text-red-600 mt-2">
                    Error: {task.error}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Task Details */}
      {selectedTask && (
        <div className="border-t p-4 bg-gray-50">
          <h3 className="font-medium mb-3">Task Details</h3>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium">ID:</span> {selectedTask.task_id}
            </div>
            <div>
              <span className="font-medium">Status:</span> {selectedTask.status}
            </div>
            <div>
              <span className="font-medium">Step:</span> {selectedTask.current_step}
            </div>
            
            {selectedTask.results && selectedTask.results.length > 0 && (
              <div>
                <span className="font-medium">Results:</span>
                <div className="mt-1 space-y-1">
                  {selectedTask.results.map((result, index) => (
                    <div key={index} className="text-xs bg-white p-2 rounded border">
                      <div className="font-medium">{result.agent}</div>
                      <div>{result.message}</div>
                      {result.error && (
                        <div className="text-red-600">{result.error}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            {selectedTask.status === 'pending' && (
              <div className="flex space-x-2 mt-3">
                <button
                  onClick={() => handleApproveTask(selectedTask.task_id, true)}
                  className="px-3 py-1 bg-green-500 text-white text-xs rounded hover:bg-green-600"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleApproveTask(selectedTask.task_id, false)}
                  className="px-3 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600"
                >
                  Reject
                </button>
              </div>
            )}

            {selectedTask.status === 'in_progress' && (
              <div className="mt-3">
                <button
                  onClick={() => handleCancelTask(selectedTask.task_id)}
                  className="px-3 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}





