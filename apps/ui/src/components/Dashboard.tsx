/**
 * Main Dashboard Component
 */

'use client';

import React, { useState, useEffect } from 'react';
import { taskApi, environmentApi, healthApi } from '@/lib/api';
import { useWebSocket } from '@/hooks/useWebSocket';

interface HealthMetrics {
  status: 'healthy' | 'warning' | 'critical';
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  load_average: number[];
  uptime: string;
}

interface Task {
  id: string;
  task_id: string;
  description: string;
  status: 'pending' | 'planning' | 'executing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}

export const Dashboard: React.FC = () => {
  const [health, setHealth] = useState<HealthMetrics | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEnv, setSelectedEnv] = useState('dev-vm');

  // WebSocket for real-time updates
  const { lastMessage, isConnected } = useWebSocket({
    url: `ws://localhost:8000/ws/dashboard`,
    onMessage: (data) => {
      if (data.type === 'task_update') {
        setTasks((prev) =>
          prev.map((task) => (task.task_id === data.task_id ? { ...task, ...data } : task))
        );
      } else if (data.type === 'health_update') {
        setHealth(data.metrics);
      }
    },
  });

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [selectedEnv]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [healthData, tasksData] = await Promise.all([
        healthApi.checkHealth(selectedEnv),
        taskApi.listTasks(10, 0),
      ]);

      setHealth(healthData);
      setTasks(tasksData.tasks);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      case 'executing':
        return 'text-blue-600 bg-blue-100';
      case 'planning':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 bg-green-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      case 'critical':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getMetricColor = (percent: number) => {
    if (percent >= 90) return 'text-red-600';
    if (percent >= 75) return 'text-yellow-600';
    return 'text-green-600';
  };

  if (loading && !health) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Monitor your DevOps infrastructure</p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <div
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}
            />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
          <select
            value={selectedEnv}
            onChange={(e) => setSelectedEnv(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            <option value="dev-vm">Development</option>
            <option value="staging">Staging</option>
            <option value="production">Production</option>
          </select>
        </div>
      </div>

      {/* Health Status */}
      {health && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Overall Status */}
          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Status</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {health.status.toUpperCase()}
                </p>
              </div>
              <div
                className={`px-3 py-1 rounded-full text-sm font-semibold ${getHealthColor(
                  health.status
                )}`}
              >
                {health.status === 'healthy' ? '✓' : health.status === 'warning' ? '⚠' : '✗'}
              </div>
            </div>
          </div>

          {/* CPU Usage */}
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm font-medium text-gray-600">CPU Usage</p>
            <div className="flex items-end justify-between mt-2">
              <p className={`text-2xl font-bold ${getMetricColor(health.cpu_percent)}`}>
                {health.cpu_percent.toFixed(1)}%
              </p>
              <div className="text-xs text-gray-500">
                Load: {health.load_average[0].toFixed(2)}
              </div>
            </div>
            <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  health.cpu_percent >= 90
                    ? 'bg-red-500'
                    : health.cpu_percent >= 75
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(health.cpu_percent, 100)}%` }}
              />
            </div>
          </div>

          {/* Memory Usage */}
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm font-medium text-gray-600">Memory Usage</p>
            <div className="flex items-end justify-between mt-2">
              <p className={`text-2xl font-bold ${getMetricColor(health.memory_percent)}`}>
                {health.memory_percent.toFixed(1)}%
              </p>
            </div>
            <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  health.memory_percent >= 90
                    ? 'bg-red-500'
                    : health.memory_percent >= 75
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(health.memory_percent, 100)}%` }}
              />
            </div>
          </div>

          {/* Disk Usage */}
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm font-medium text-gray-600">Disk Usage</p>
            <div className="flex items-end justify-between mt-2">
              <p className={`text-2xl font-bold ${getMetricColor(health.disk_percent)}`}>
                {health.disk_percent.toFixed(1)}%
              </p>
            </div>
            <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  health.disk_percent >= 90
                    ? 'bg-red-500'
                    : health.disk_percent >= 75
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(health.disk_percent, 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Recent Tasks */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">Recent Tasks</h2>
            <button
              onClick={loadData}
              className="px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>
        <div className="divide-y divide-gray-200">
          {tasks.length === 0 ? (
            <div className="px-6 py-12 text-center text-gray-500">
              <p>No tasks yet</p>
              <p className="text-sm mt-1">Create a task to get started</p>
            </div>
          ) : (
            tasks.map((task) => (
              <div
                key={task.task_id}
                className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => (window.location.href = `/tasks/${task.task_id}`)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3">
                      <span
                        className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(
                          task.status
                        )}`}
                      >
                        {task.status}
                      </span>
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {task.description}
                      </p>
                    </div>
                    <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                      <span>ID: {task.task_id}</span>
                      <span>
                        Created: {new Date(task.created_at).toLocaleDateString()} at{' '}
                        {new Date(task.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                  <div className="ml-4">
                    <svg
                      className="w-5 h-5 text-gray-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <button
          onClick={() => (window.location.href = '/tasks/new')}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-6 rounded-lg shadow transition-colors flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          <span>Create New Task</span>
        </button>

        <button
          onClick={() => (window.location.href = '/terminal')}
          className="bg-gray-800 hover:bg-gray-900 text-white font-semibold py-4 px-6 rounded-lg shadow transition-colors flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <span>Open Terminal</span>
        </button>

        <button
          onClick={() => (window.location.href = '/settings')}
          className="bg-white hover:bg-gray-50 text-gray-700 font-semibold py-4 px-6 rounded-lg shadow border border-gray-300 transition-colors flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
};

export default Dashboard;
