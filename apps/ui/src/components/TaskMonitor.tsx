'use client'

import { useState, useEffect } from 'react'
import { Clock, CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react'
import { Task } from '@/types/task'
import { taskApi } from '@/lib/api'

interface TaskMonitorProps {
  tasks: Task[]
  onTaskUpdate: () => void
  className?: string
}

export function TaskMonitor({ tasks, onTaskUpdate, className }: TaskMonitorProps) {
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
        return <CheckCircle className="h-4 w-4 text-emerald-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-rose-500" />
      case 'in_progress':
        return <Clock className="h-4 w-4 text-indigo-500 animate-pulse" />
      case 'pending':
        return <AlertCircle className="h-4 w-4 text-amber-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-emerald-100 text-emerald-700'
      case 'failed':
        return 'bg-rose-100 text-rose-700'
      case 'in_progress':
        return 'bg-indigo-100 text-indigo-700'
      case 'pending':
        return 'bg-amber-100 text-amber-700'
      default:
        return 'bg-gray-100 text-gray-700'
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

  const containerClassName = ['flex', 'h-full', 'flex-col']
  if (className) {
    containerClassName.push(className)
  }

  return (
    <div className={containerClassName.join(' ')}>
      {/* Header */}
      <div className="border-b border-gray-100 bg-white px-4 py-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">Монитор задач</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`rounded p-1 ${autoRefresh ? 'text-indigo-500' : 'text-gray-400'}`}
              title={autoRefresh ? 'Автообновление включено' : 'Включить автообновление'}
            >
              <RefreshCw className={`h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onTaskUpdate}
              className="rounded p-1 text-gray-400 transition hover:text-gray-600"
              title="Обновить сейчас"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {tasks.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-gray-200 bg-white/60 py-8 text-center">
            <Clock className="mx-auto mb-4 h-12 w-12 text-gray-300" />
            <p className="text-sm text-gray-500">Активные задачи отсутствуют</p>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <div
                key={task.task_id}
                className={`cursor-pointer rounded-2xl border border-gray-200 bg-white px-3 py-3 shadow-sm transition hover:border-indigo-200 hover:bg-indigo-50/60 ${
                  selectedTask?.task_id === task.task_id ? 'ring-1 ring-indigo-400' : ''
                }`}
                onClick={() => setSelectedTask(task)}
              >
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(task.status)}
                    <span className="text-sm font-medium text-gray-900">
                      {task.task_id.slice(0, 8)}…
                    </span>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusColor(
                      task.status
                    )}`}
                  >
                    {task.status}
                  </span>
                </div>
                <div className="text-sm text-gray-600">{task.current_step}</div>
                {task.error && (
                  <div className="mt-2 rounded-lg bg-rose-50 p-2 text-sm text-rose-600">
                    Ошибка: {task.error}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Task Details */}
      {selectedTask && (
        <div className="border-t border-gray-100 bg-slate-50 px-4 py-4">
          <h3 className="mb-3 text-sm font-semibold text-gray-900">Детали задачи</h3>
          <div className="space-y-2 text-xs text-gray-700">
            <div>
              <span className="font-medium text-gray-600">ID:</span> {selectedTask.task_id}
            </div>
            <div>
              <span className="font-medium text-gray-600">Статус:</span> {selectedTask.status}
            </div>
            <div>
              <span className="font-medium text-gray-600">Шаг:</span> {selectedTask.current_step}
            </div>

            {selectedTask.results && selectedTask.results.length > 0 && (
              <div>
                <span className="font-medium text-gray-600">Результаты:</span>
                <div className="mt-1 space-y-2">
                  {selectedTask.results.map((result, index) => (
                    <div
                      key={index}
                      className="rounded-xl border border-gray-200 bg-white p-3 text-xs shadow-sm"
                    >
                      <div className="font-medium text-gray-800">{result.agent}</div>
                      <div className="text-gray-600">{result.message}</div>
                      {result.error && (
                        <div className="mt-1 text-rose-600">{result.error}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedTask.status === 'pending' && (
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => handleApproveTask(selectedTask.task_id, true)}
                  className="inline-flex items-center rounded-lg bg-emerald-500 px-3 py-1 text-xs font-medium text-white shadow-sm hover:bg-emerald-600"
                >
                  Одобрить
                </button>
                <button
                  onClick={() => handleApproveTask(selectedTask.task_id, false)}
                  className="inline-flex items-center rounded-lg bg-rose-500 px-3 py-1 text-xs font-medium text-white shadow-sm hover:bg-rose-600"
                >
                  Отклонить
                </button>
              </div>
            )}

            {selectedTask.status === 'in_progress' && (
              <div className="mt-4">
                <button
                  onClick={() => handleCancelTask(selectedTask.task_id)}
                  className="inline-flex items-center rounded-lg bg-rose-500 px-3 py-1 text-xs font-medium text-white shadow-sm hover:bg-rose-600"
                >
                  Отменить задачу
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
