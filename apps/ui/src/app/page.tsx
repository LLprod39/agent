'use client'

import { useState, useEffect } from 'react'
import { MessageSquare, Settings, TestTube, GitBranch } from 'lucide-react'
import { ChatInterface } from '@/components/ChatInterface'
import { TaskMonitor } from '@/components/TaskMonitor'
import { Header } from '@/components/Header'
import { Sidebar } from '@/components/Sidebar'
import { SettingsPanel } from '@/components/SettingsPanel'
import { AgentTester } from '@/components/AgentTester'
import { WorkflowViewer } from '@/components/WorkflowViewer'
import { environmentApi, taskApi, healthApi, API_BASE_URL } from '@/lib/api'
import { Environment } from '@/types/environment'
import { Task } from '@/types/task'

type ViewType = 'chat' | 'settings' | 'testing' | 'workflow'

export default function Home() {
  const [selectedEnvironment, setSelectedEnvironment] = useState<Environment | null>(null)
  const [environments, setEnvironments] = useState<Environment[]>([])
  const [activeTasks, setActiveTasks] = useState<Task[]>([])
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [currentView, setCurrentView] = useState<ViewType>('chat')
  const [apiError, setApiError] = useState<string | null>(null)

  useEffect(() => {
    loadEnvironments()
    loadActiveTasks()
    checkHealth()
  }, [])

  const loadEnvironments = async () => {
    try {
      const data = await environmentApi.listEnvironments()
      const envs = data.environments || []
      setEnvironments(envs)
      if (envs.length > 0) {
        setSelectedEnvironment(envs[0])
      }
    } catch (error) {
      console.error('Failed to load environments:', error)
      setApiError(`Не удалось получить список окружений с API (${API_BASE_URL}). Убедитесь, что backend запущен.`)
    }
  }

  const loadActiveTasks = async () => {
    try {
      const data = await taskApi.listTasks()
      setActiveTasks(data.tasks || [])
    } catch (error) {
      console.error('Failed to load active tasks:', error)
      setApiError(`Не удалось получить список задач с API (${API_BASE_URL}). Проверьте состояние сервера.`)
    }
  }

  const checkHealth = async () => {
    try {
      await healthApi.checkHealth()
      setApiError(null)
    } catch (error) {
      console.error('API health check failed:', error)
      setApiError(`API недоступно по адресу ${API_BASE_URL}. Запустите backend (uvicorn apps.api.main:app).`)
    }
  }

  const handleTaskSelect = (task: Task) => {
    setSelectedTask(task)
    setCurrentView('workflow')
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left Sidebar - Navigation */}
      <div className="w-16 bg-gray-900 text-white flex flex-col items-center py-4 space-y-4">
        <button
          onClick={() => setCurrentView('chat')}
          className={`p-3 rounded-lg transition-colors ${
            currentView === 'chat' ? 'bg-blue-600' : 'hover:bg-gray-800'
          }`}
          title="Чат"
        >
          <MessageSquare className="h-6 w-6" />
        </button>
        <button
          onClick={() => setCurrentView('settings')}
          className={`p-3 rounded-lg transition-colors ${
            currentView === 'settings' ? 'bg-blue-600' : 'hover:bg-gray-800'
          }`}
          title="Настройки"
        >
          <Settings className="h-6 w-6" />
        </button>
        <button
          onClick={() => setCurrentView('testing')}
          className={`p-3 rounded-lg transition-colors ${
            currentView === 'testing' ? 'bg-blue-600' : 'hover:bg-gray-800'
          }`}
          title="Тестирование"
        >
          <TestTube className="h-6 w-6" />
        </button>
        <button
          onClick={() => setCurrentView('workflow')}
          className={`p-3 rounded-lg transition-colors ${
            currentView === 'workflow' ? 'bg-blue-600' : 'hover:bg-gray-800'
          }`}
          title="Workflow"
        >
          <GitBranch className="h-6 w-6" />
        </button>
      </div>

      {/* Mobile Sidebar */}
      <Sidebar 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)}
        activeTasks={activeTasks}
        onTaskUpdate={loadActiveTasks}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <Header 
          onMenuClick={() => setSidebarOpen(true)}
          selectedEnvironment={selectedEnvironment}
          onEnvironmentChange={setSelectedEnvironment}
        />

        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main View */}
          <div className="flex-1 flex flex-col">
            {apiError && (
              <div className="mx-6 mt-4 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
                {apiError}
              </div>
            )}

            {currentView === 'chat' && (
              <ChatInterface 
                selectedEnvironment={selectedEnvironment}
                onTaskCreated={loadActiveTasks}
              />
            )}
            
            {currentView === 'settings' && (
              <SettingsPanel />
            )}
            
            {currentView === 'testing' && (
              <AgentTester environments={environments} />
            )}
            
            {currentView === 'workflow' && (
              <WorkflowViewer task={selectedTask} />
            )}
          </div>

          {/* Right Sidebar - Task Monitor */}
          {currentView === 'chat' && (
            <div className="w-80 border-l border-gray-200 bg-white">
              <TaskMonitor 
                tasks={activeTasks}
                onTaskUpdate={loadActiveTasks}
              />
            </div>
          )}

          {/* Task List for Workflow View */}
          {currentView === 'workflow' && (
            <div className="w-80 border-l border-gray-200 bg-white">
              <div className="p-4 border-b">
                <h2 className="text-lg font-semibold">Выберите задачу</h2>
              </div>
              <div className="overflow-y-auto p-4 space-y-2">
                {activeTasks.map((task) => (
                  <button
                    key={task.task_id}
                    onClick={() => handleTaskSelect(task)}
                    className={`w-full text-left p-3 border rounded-lg hover:bg-gray-50 transition-colors ${
                      selectedTask?.task_id === task.task_id ? 'bg-blue-50 border-blue-500' : ''
                    }`}
                  >
                    <p className="font-medium text-sm">{task.task_id.slice(0, 8)}...</p>
                    <p className="text-xs text-gray-600">{task.status}</p>
                  </button>
                ))}
                {activeTasks.length === 0 && (
                  <p className="text-sm text-gray-500 text-center py-8">
                    Нет активных задач
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}





