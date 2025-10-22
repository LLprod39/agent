/**
 * Task List Component with filtering and pagination
 */

'use client';

import React, { useState, useEffect } from 'react';
import { taskApi } from '@/lib/api';

interface Task {
  id: string;
  task_id: string;
  description: string;
  status: 'pending' | 'planning' | 'executing' | 'completed' | 'failed' | 'cancelled';
  environment_profile: string;
  created_at: string;
  updated_at: string;
  user_id?: number;
  result?: any;
}

interface TaskListProps {
  onTaskClick?: (taskId: string) => void;
}

export const TaskList: React.FC<TaskListProps> = ({ onTaskClick }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filteredTasks, setFilteredTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [environmentFilter, setEnvironmentFilter] = useState<string>('all');

  // Pagination
  const [page, setPage] = useState(1);
  const [totalTasks, setTotalTasks] = useState(0);
  const pageSize = 20;

  useEffect(() => {
    loadTasks();
  }, [page]);

  useEffect(() => {
    applyFilters();
  }, [tasks, statusFilter, searchQuery, environmentFilter]);

  const loadTasks = async () => {
    try {
      setLoading(true);
      setError(null);

      const offset = (page - 1) * pageSize;
      const response = await taskApi.listTasks(pageSize, offset);

      setTasks(response.tasks);
      setTotalTasks(response.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load tasks');
      console.error('Error loading tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...tasks];

    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter((task) => task.status === statusFilter);
    }

    // Environment filter
    if (environmentFilter !== 'all') {
      filtered = filtered.filter((task) => task.environment_profile === environmentFilter);
    }

    // Search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (task) =>
          task.description.toLowerCase().includes(query) ||
          task.task_id.toLowerCase().includes(query)
      );
    }

    setFilteredTasks(filtered);
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

    const icons = {
      completed: '✓',
      failed: '✗',
      executing: '⟳',
      planning: '◷',
      pending: '○',
      cancelled: '⊘',
    };

    return (
      <span
        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${
          styles[status as keyof typeof styles] || styles.pending
        }`}
      >
        <span className="mr-1">{icons[status as keyof typeof icons] || '○'}</span>
        {status.toUpperCase()}
      </span>
    );
  };

  const getEnvironmentBadge = (env: string) => {
    const colors = {
      production: 'bg-red-50 text-red-700 border-red-200',
      staging: 'bg-yellow-50 text-yellow-700 border-yellow-200',
      'dev-vm': 'bg-blue-50 text-blue-700 border-blue-200',
      development: 'bg-blue-50 text-blue-700 border-blue-200',
    };

    return (
      <span
        className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${
          colors[env as keyof typeof colors] || 'bg-gray-50 text-gray-700 border-gray-200'
        }`}
      >
        {env}
      </span>
    );
  };

  const handleTaskClick = (taskId: string) => {
    if (onTaskClick) {
      onTaskClick(taskId);
    } else {
      window.location.href = `/tasks/${taskId}`;
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  };

  const totalPages = Math.ceil(totalTasks / pageSize);

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow">
      {/* Header and Filters */}
      <div className="px-6 py-4 border-b border-gray-200 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Tasks</h2>
          <button
            onClick={loadTasks}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {/* Search and Filters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <svg
              className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="planning">Planning</option>
            <option value="executing">Executing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>

          {/* Environment Filter */}
          <select
            value={environmentFilter}
            onChange={(e) => setEnvironmentFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            <option value="all">All Environments</option>
            <option value="dev-vm">Development</option>
            <option value="staging">Staging</option>
            <option value="production">Production</option>
          </select>
        </div>

        {/* Results count */}
        <div className="text-sm text-gray-600">
          Showing {filteredTasks.length} of {totalTasks} tasks
        </div>
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto">
        {error ? (
          <div className="px-6 py-12 text-center">
            <div className="text-red-600 mb-2">Error loading tasks</div>
            <div className="text-sm text-gray-600">{error}</div>
            <button
              onClick={loadTasks}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Retry
            </button>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            <svg
              className="mx-auto h-12 w-12 text-gray-400 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <p className="text-lg font-medium">No tasks found</p>
            <p className="text-sm mt-1">
              {searchQuery || statusFilter !== 'all' || environmentFilter !== 'all'
                ? 'Try adjusting your filters'
                : 'Create your first task to get started'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredTasks.map((task) => (
              <div
                key={task.task_id}
                onClick={() => handleTaskClick(task.task_id)}
                className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    {/* Status and Environment */}
                    <div className="flex items-center space-x-2 mb-2">
                      {getStatusBadge(task.status)}
                      {getEnvironmentBadge(task.environment_profile)}
                    </div>

                    {/* Description */}
                    <p className="text-sm font-medium text-gray-900 mb-1">
                      {task.description}
                    </p>

                    {/* Metadata */}
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span className="font-mono">{task.task_id}</span>
                      <span>Created {formatDate(task.created_at)}</span>
                      {task.updated_at !== task.created_at && (
                        <span>Updated {formatDate(task.updated_at)}</span>
                      )}
                    </div>
                  </div>

                  {/* Arrow */}
                  <div className="ml-4 flex-shrink-0">
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
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>

            <div className="flex items-center space-x-2">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const pageNum = i + 1;
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                      page === pageNum
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
              {totalPages > 5 && (
                <>
                  <span className="text-gray-500">...</span>
                  <button
                    onClick={() => setPage(totalPages)}
                    className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                      page === totalPages
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    {totalPages}
                  </button>
                </>
              )}
            </div>

            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskList;
