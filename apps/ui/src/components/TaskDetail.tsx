/**
 * Task Detail Component - Shows comprehensive task information
 */

'use client';

import React, { useState, useEffect } from 'react';
import { taskApi } from '@/lib/api';
import { useWebSocket } from '@/hooks/useWebSocket';

interface TaskStep {
  step_id: string;
  step_number: number;
  description: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  command?: string;
  output?: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

interface Task {
  id: string;
  task_id: string;
  description: string;
  status: 'pending' | 'planning' | 'executing' | 'completed' | 'failed' | 'cancelled';
  environment_profile: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  user_id?: number;
  result?: any;
  error?: string;
  steps?: TaskStep[];
}

interface TaskDetailProps {
  taskId: string;
  onClose?: () => void;
}

export const TaskDetail: React.FC<TaskDetailProps> = ({ taskId, onClose }) => {
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // WebSocket for real-time updates
  const { lastMessage, isConnected } = useWebSocket({
    url: `ws://localhost:8000/ws/tasks/${taskId}`,
    onMessage: (data) => {
      if (data.type === 'task_update' && data.task_id === taskId) {
        setTask((prev) => (prev ? { ...prev, ...data.task } : data.task));
      } else if (data.type === 'step_update' && data.task_id === taskId) {
        setTask((prev) => {
          if (!prev) return prev;
          const steps = prev.steps || [];
          const stepIndex = steps.findIndex((s) => s.step_id === data.step.step_id);
          if (stepIndex >= 0) {
            steps[stepIndex] = { ...steps[stepIndex], ...data.step };
          } else {
            steps.push(data.step);
          }
          return { ...prev, steps: steps.sort((a, b) => a.step_number - b.step_number) };
        });
      }
    },
  });

  useEffect(() => {
    loadTask();

    // Auto-refresh for active tasks
    const interval = setInterval(() => {
      if (
        autoRefresh &&
        task &&
        ['pending', 'planning', 'executing'].includes(task.status)
      ) {
        loadTask();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [taskId, autoRefresh]);

  const loadTask = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await taskApi.getTask(taskId);
      setTask(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load task');
      console.error('Error loading task:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (approved: boolean) => {
    try {
      await taskApi.approveTask(taskId, approved);
      await loadTask();
    } catch (err: any) {
      alert(`Failed to ${approved ? 'approve' : 'reject'} task: ${err.message}`);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      completed: 'bg-green-100 text-green-800 border-green-200',
      failed: 'bg-red-100 text-red-800 border-red-200',
      executing: 'bg-blue-100 text-blue-800 border-blue-200',
      planning: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      pending: 'bg-gray-100 text-gray-800 border-gray-200',
      cancelled: 'bg-gray-100 text-gray-600 border-gray-200',
    };

    return (
      <span
        className={`inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold border ${
          styles[status as keyof typeof styles] || styles.pending
        }`}
      >
        {status.toUpperCase()}
      </span>
    );
  };

  const getStepStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="text-green-600">✓</span>;
      case 'failed':
        return <span className="text-red-600">✗</span>;
      case 'executing':
        return <span className="text-blue-600 animate-pulse">⟳</span>;
      default:
        return <span className="text-gray-400">○</span>;
    }
  };

  const formatDuration = (start?: string, end?: string) => {
    if (!start) return '-';
    const startTime = new Date(start).getTime();
    const endTime = end ? new Date(end).getTime() : Date.now();
    const diffMs = endTime - startTime;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);

    if (diffMin > 0) {
      return `${diffMin}m ${diffSec % 60}s`;
    }
    return `${diffSec}s`;
  };

  if (loading && !task) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-red-600 text-lg mb-2">Error Loading Task</div>
          <div className="text-gray-600 mb-4">{error || 'Task not found'}</div>
          <button
            onClick={loadTask}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <h2 className="text-2xl font-bold text-gray-900">Task Details</h2>
            {getStatusBadge(task.status)}
            {isConnected && (
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span>Live</span>
              </div>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <label className="flex items-center space-x-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              <span>Auto-refresh</span>
            </label>
            <button
              onClick={loadTask}
              className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded transition-colors"
            >
              Refresh
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
              >
                Close
              </button>
            )}
          </div>
        </div>

        {/* Task Info */}
        <div className="space-y-2 text-sm">
          <div className="flex items-center space-x-2">
            <span className="font-medium text-gray-700">Task ID:</span>
            <span className="font-mono text-gray-900">{task.task_id}</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="font-medium text-gray-700">Environment:</span>
            <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-medium">
              {task.environment_profile}
            </span>
          </div>
          <div className="flex items-center space-x-4 text-gray-600">
            <span>Created: {new Date(task.created_at).toLocaleString()}</span>
            {task.completed_at && (
              <span>
                Completed: {new Date(task.completed_at).toLocaleString()} (
                {formatDuration(task.created_at, task.completed_at)})
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Task Description */}
      <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Description</h3>
        <p className="text-gray-900">{task.description}</p>
      </div>

      {/* Task Steps */}
      {task.steps && task.steps.length > 0 && (
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Execution Steps</h3>
          <div className="space-y-4">
            {task.steps.map((step) => (
              <div
                key={step.step_id}
                className="border border-gray-200 rounded-lg overflow-hidden"
              >
                {/* Step Header */}
                <div className="px-4 py-3 bg-gray-50 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="text-lg">{getStepStatusIcon(step.status)}</span>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-gray-900">
                          Step {step.step_number}
                        </span>
                        <span className="text-sm text-gray-600">{step.description}</span>
                      </div>
                      {step.started_at && (
                        <div className="text-xs text-gray-500 mt-1">
                          Duration: {formatDuration(step.started_at, step.completed_at)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Step Command */}
                {step.command && (
                  <div className="px-4 py-3 bg-gray-900 text-white">
                    <div className="text-xs text-gray-400 mb-1">Command</div>
                    <pre className="font-mono text-sm whitespace-pre-wrap">{step.command}</pre>
                  </div>
                )}

                {/* Step Output */}
                {step.output && (
                  <div className="px-4 py-3 bg-gray-800 text-gray-100">
                    <div className="text-xs text-gray-400 mb-1">Output</div>
                    <pre className="font-mono text-xs whitespace-pre-wrap max-h-60 overflow-y-auto">
                      {step.output}
                    </pre>
                  </div>
                )}

                {/* Step Error */}
                {step.error && (
                  <div className="px-4 py-3 bg-red-50 text-red-900">
                    <div className="text-xs text-red-700 mb-1 font-semibold">Error</div>
                    <pre className="font-mono text-xs whitespace-pre-wrap">{step.error}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Task Result */}
      {task.result && (
        <div className="px-6 py-4 border-t border-gray-200 bg-green-50">
          <h3 className="text-sm font-semibold text-green-800 mb-2">Result</h3>
          <pre className="text-sm text-gray-900 whitespace-pre-wrap">
            {typeof task.result === 'string' ? task.result : JSON.stringify(task.result, null, 2)}
          </pre>
        </div>
      )}

      {/* Task Error */}
      {task.error && (
        <div className="px-6 py-4 border-t border-gray-200 bg-red-50">
          <h3 className="text-sm font-semibold text-red-800 mb-2">Error</h3>
          <pre className="text-sm text-red-900 whitespace-pre-wrap">{task.error}</pre>
        </div>
      )}

      {/* Approval Actions */}
      {task.status === 'pending' && (
        <div className="px-6 py-4 border-t border-gray-200 bg-yellow-50">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-yellow-800">Approval Required</h3>
              <p className="text-xs text-yellow-700 mt-1">
                This task requires approval before execution
              </p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={() => handleApprove(false)}
                className="px-4 py-2 bg-white border border-red-300 text-red-700 rounded-lg hover:bg-red-50 transition-colors font-medium"
              >
                Reject
              </button>
              <button
                onClick={() => handleApprove(true)}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
              >
                Approve
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskDetail;
