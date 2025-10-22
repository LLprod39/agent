'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  MessageSquare,
  Server,
  Settings2,
  TestTube,
  GitBranch,
  AlertCircle,
} from 'lucide-react'
import { ChatInterface } from '@/components/ChatInterface'
import { TaskMonitor } from '@/components/TaskMonitor'
import { Header } from '@/components/Header'
import { Sidebar } from '@/components/Sidebar'
import { SettingsPanel } from '@/components/SettingsPanel'
import { AgentTester } from '@/components/AgentTester'
import { WorkflowViewer } from '@/components/WorkflowViewer'
import { MachineManager } from '@/components/MachineManager'
import { environmentApi, taskApi, healthApi, API_BASE_URL } from '@/lib/api'
import { Environment } from '@/types/environment'
import { Task } from '@/types/task'

type ViewType = 'chat' | 'machines' | 'settings' | 'testing' | 'workflow'

const navigation: Array<{
  id: ViewType
  label: string
  description: string
  icon: typeof MessageSquare
}> = [
  {
    id: 'chat',
    label: 'Чат',
    description: 'Диалог с агентом',
    icon: MessageSquare,
  },
  {
    id: 'machines',
    label: 'Серверы',
    description: 'SSH машины и доступы',
    icon: Server,
  },
  {
    id: 'testing',
    label: 'Тесты',
    description: 'Проверка агентов',
    icon: TestTube,
  },
  {
    id: 'workflow',
    label: 'Workflow',
    description: 'История задач',
    icon: GitBranch,
  },
  {
    id: 'settings',
    label: 'Настройки',
    description: 'Провайдеры и интеграции',
    icon: Settings2,
  },
]

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
        const preferred =
          envs.find((env) => env.id === selectedEnvironment?.id) ?? envs[0]
        setSelectedEnvironment(preferred)
      } else {
        setSelectedEnvironment(null)
      }
    } catch (error) {
      console.error('Failed to load environments:', error)
      setApiError(
        `Не удалось загрузить окружения из API (${API_BASE_URL}). Проверьте, что backend запущен.`
      )
    }
  }

  const loadActiveTasks = async () => {
    try {
      const data = await taskApi.listTasks()
      setActiveTasks(data.tasks || [])
    } catch (error) {
      console.error('Failed to load active tasks:', error)
      setApiError(
        `Не удалось получить список задач из API (${API_BASE_URL}). Убедитесь, что сервис доступен.`
      )
    }
  }

  const checkHealth = async () => {
    try {
      await healthApi.checkHealth()
      setApiError(null)
    } catch (error) {
      console.error('API health check failed:', error)
      setApiError(
        `API недоступно по адресу ${API_BASE_URL}. Запустите backend командой uvicorn apps.api.main:app.`
      )
    }
  }

  const handleTaskSelect = (task: Task) => {
    setSelectedTask(task)
    setCurrentView('workflow')
  }

  const tasksByStatus = useMemo(() => activeTasks.length, [activeTasks])

  return (
    <div className="flex min-h-screen bg-slate-100">
      {/* Desktop navigation */}
      <aside className="hidden w-64 flex-col border-r border-slate-200 bg-white/80 px-3 py-6 backdrop-blur xl:flex">
        <div className="mb-8 px-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Навигация
          </h2>
        </div>
        <nav className="space-y-2">
          {navigation.map((item) => {
            const isActive = currentView === item.id
            const Icon = item.icon
            return (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                  isActive
                    ? 'border-indigo-200 bg-indigo-50 text-indigo-600 shadow-sm'
                    : 'border-transparent text-slate-600 hover:border-slate-200 hover:bg-white'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`rounded-xl p-2 ${
                      isActive ? 'bg-white text-indigo-600' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="text-sm font-semibold">{item.label}</p>
                    <p className="text-xs text-slate-500">{item.description}</p>
                  </div>
                </div>
              </button>
            )
          })}
        </nav>

        <div className="mt-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Активных задач:</p>
          <p className="text-2xl font-semibold text-slate-900">{tasksByStatus}</p>
          <p className="mt-2 text-xs text-slate-500">
            Обновляйте монитор, чтобы видеть прогресс выполнения операций.
          </p>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col">
        <Header
          onMenuClick={() => setSidebarOpen(true)}
          selectedEnvironment={selectedEnvironment}
          onEnvironmentChange={setSelectedEnvironment}
        />

        <main className="flex-1 overflow-hidden">
          <div className="mx-auto flex h-full max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
            {apiError && (
              <div className="mb-4 flex items-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
                <AlertCircle className="h-4 w-4" />
                <span>{apiError}</span>
              </div>
            )}

            <div className="relative flex-1 overflow-hidden rounded-3xl bg-white/60 shadow-inner">
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-50 via-white to-slate-50" />
              <div className="relative h-full overflow-y-auto px-6 py-6">
                {currentView === 'chat' && (
                  <div className="grid h-full gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
                    <div className="rounded-3xl border border-slate-200 bg-white shadow-sm">
                      <ChatInterface
                        selectedEnvironment={selectedEnvironment}
                        onTaskCreated={loadActiveTasks}
                      />
                    </div>
                    <div className="rounded-3xl border border-slate-200 bg-white shadow-sm">
                      <TaskMonitor
                        tasks={activeTasks}
                        onTaskUpdate={loadActiveTasks}
                        className="rounded-3xl"
                      />
                    </div>
                  </div>
                )}

                {currentView === 'machines' && (
                  <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                    <MachineManager
                      environments={environments}
                      onRefresh={loadEnvironments}
                      onSelectEnvironment={(env) => {
                        setSelectedEnvironment(env)
                        setCurrentView('chat')
                      }}
                    />
                  </div>
                )}

                {currentView === 'settings' && (
                  <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                    <SettingsPanel />
                  </div>
                )}

                {currentView === 'testing' && (
                  <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                    <AgentTester environments={environments} />
                  </div>
                )}

                {currentView === 'workflow' && (
                  <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
                    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                      <WorkflowViewer task={selectedTask} />
                    </div>
                    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
                      <h2 className="mb-3 text-base font-semibold text-slate-900">
                        Недавние задачи
                      </h2>
                      <div className="space-y-2">
                        {activeTasks.map((task) => (
                          <button
                            key={task.task_id}
                            onClick={() => handleTaskSelect(task)}
                            className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                              selectedTask?.task_id === task.task_id
                                ? 'border-indigo-200 bg-indigo-50 text-indigo-600'
                                : 'border-slate-200 bg-white text-slate-700 hover:border-indigo-200 hover:bg-indigo-50/60'
                            }`}
                          >
                            <p className="text-sm font-medium">
                              {task.task_id.slice(0, 10)}…
                            </p>
                            <p className="text-xs text-slate-500">{task.status}</p>
                          </button>
                        ))}
                        {activeTasks.length === 0 && (
                          <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-xs text-slate-500">
                            Нет задач для отображения.
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Mobile task sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        activeTasks={activeTasks}
        onTaskUpdate={loadActiveTasks}
      />
    </div>
  )
}

