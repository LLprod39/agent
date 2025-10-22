'use client'

import { useState } from 'react'
import { Play, Clock, CheckCircle, XCircle, Loader2, Activity } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { Environment } from '@/types/environment'

interface AgentTesterProps {
  environments: Environment[]
}

interface TestResult {
  test_id: string
  status: string
  result: any
  error?: string
  execution_time?: number
}

export function AgentTester({ environments }: AgentTesterProps) {
  const [task, setTask] = useState('')
  const [selectedEnvironment, setSelectedEnvironment] = useState<string>('')
  const [agentType, setAgentType] = useState<'planner' | 'executor' | 'verifier'>('planner')
  const [autoApprove, setAutoApprove] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [testResults, setTestResults] = useState<TestResult[]>([])

  const handleRunTest = async () => {
    if (!task.trim()) return

    setIsRunning(true)
    try {
      const result = await adminApi.testAgent({
        task: task.trim(),
        environment_profile: selectedEnvironment || undefined,
        agent_type: agentType,
        auto_approve: autoApprove,
      })

      setTestResults(prev => [result, ...prev])
    } catch (error) {
      console.error('Failed to run agent test:', error)
    } finally {
      setIsRunning(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return <Clock className="h-5 w-5 text-gray-500" />
    }
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b p-6">
        <div className="flex items-center space-x-3 mb-6">
          <Activity className="h-6 w-6 text-gray-700" />
          <h1 className="text-2xl font-bold text-gray-900">Тестирование агентов</h1>
        </div>

        {/* Test Configuration */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Задача для тестирования
            </label>
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Например: Проверить статус всех подов в namespace default"
              className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
              disabled={isRunning}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Окружение
              </label>
              <select
                value={selectedEnvironment}
                onChange={(e) => setSelectedEnvironment(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isRunning}
              >
                <option value="">Без окружения</option>
                {environments.map((env) => (
                  <option key={env.id} value={env.id}>
                    {env.display_name || env.id}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Тип агента
              </label>
              <select
                value={agentType}
                onChange={(e) => setAgentType(e.target.value as any)}
                className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isRunning}
              >
                <option value="planner">Planner (Планировщик)</option>
                <option value="executor">Executor (Исполнитель)</option>
                <option value="verifier">Verifier (Проверяльщик)</option>
              </select>
            </div>

            <div className="flex items-end">
              <label className="flex items-center space-x-2 p-2 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={autoApprove}
                  onChange={(e) => setAutoApprove(e.target.checked)}
                  disabled={isRunning}
                  className="w-4 h-4 text-blue-600"
                />
                <span className="text-sm font-medium text-gray-700">
                  Автоматическое подтверждение
                </span>
              </label>
            </div>
          </div>

          <button
            onClick={handleRunTest}
            disabled={!task.trim() || isRunning}
            className="w-full flex items-center justify-center space-x-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRunning ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Выполняется тест...</span>
              </>
            ) : (
              <>
                <Play className="h-5 w-5" />
                <span>Запустить тест</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Test Results */}
      <div className="flex-1 overflow-y-auto p-6">
        <h2 className="text-lg font-semibold mb-4">Результаты тестов</h2>
        
        {testResults.length === 0 ? (
          <div className="text-center py-12">
            <Activity className="h-16 w-16 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500">Пока нет результатов тестирования</p>
            <p className="text-sm text-gray-400 mt-2">
              Запустите тест агента, чтобы увидеть результаты здесь
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {testResults.map((result) => (
              <div key={result.test_id} className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(result.status)}
                    <div>
                      <p className="font-medium">Test ID: {result.test_id}</p>
                      <p className="text-sm text-gray-600">
                        Статус: <span className={`font-medium ${
                          result.status === 'success' ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {result.status}
                        </span>
                      </p>
                    </div>
                  </div>
                  {result.execution_time && (
                    <div className="text-right">
                      <p className="text-sm text-gray-600">Время выполнения</p>
                      <p className="font-medium">{result.execution_time.toFixed(2)}s</p>
                    </div>
                  )}
                </div>

                {result.error && (
                  <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm font-medium text-red-800">Ошибка:</p>
                    <p className="text-sm text-red-700 mt-1">{result.error}</p>
                  </div>
                )}

                {result.result && (
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-2">Результат:</p>
                    <div className="bg-gray-50 rounded-lg p-4 overflow-auto">
                      <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                        {JSON.stringify(result.result, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
