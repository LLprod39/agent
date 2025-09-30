'use client'

import { useState, useEffect } from 'react'
import { X, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { Task } from '@/types/task'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  activeTasks: Task[]
  onTaskUpdate: () => void
}

export function Sidebar({ isOpen, onClose, activeTasks, onTaskUpdate }: SidebarProps) {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  useEffect(() => {
    // Auto-refresh tasks every 5 seconds
    const interval = setInterval(() => {
      onTaskUpdate()
    }, 5000)

    return () => clearInterval(interval)
  }, [onTaskUpdate])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'in_progress':
        return <Clock className="h-4 w-4 text-blue-500" />
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

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />
      
      <div className="fixed left-0 top-0 h-full w-80 bg-white shadow-xl">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Task Monitor</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-md hover:bg-gray-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {activeTasks.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <Clock className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No active tasks</p>
            </div>
          ) : (
            <div className="space-y-3">
              {activeTasks.map((task) => (
                <div
                  key={task.task_id}
                  className={`p-3 border rounded-lg cursor-pointer hover:bg-gray-50 ${
                    selectedTask?.task_id === task.task_id ? 'ring-2 ring-blue-500' : ''
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
          <div className="border-t p-4">
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
                      <div key={index} className="text-xs bg-gray-100 p-2 rounded">
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
            </div>
          </div>
        )}
      </div>
    </div>
  )
}






