'use client'

import { useState, useEffect } from 'react'
import { Settings, Database, Server, Cpu, RefreshCw, CheckCircle, XCircle, Activity, Key, TestTube, AlertCircle, Play, Edit } from 'lucide-react'
import { adminApi } from '@/lib/api'
import { ProviderConfigModal } from './ProviderConfigModal'

interface SystemInfo {
  version: string
  components: {
    llm_providers: {
      available: string[]
      healthy: string[]
      models: Record<string, string[]>
    }
    cache: {
      enabled: boolean
      stats: any
    }
    redis: {
      enabled: boolean
      healthy: boolean
    }
    database: {
      enabled: boolean
      healthy: boolean
    }
  }
  features: Record<string, boolean>
}

export function SettingsPanel() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [llmConfig, setLLMConfig] = useState<any>(null)
  const [providersHealth, setProvidersHealth] = useState<any>(null)
  const [cacheStats, setCacheStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'system' | 'llm' | 'cache' | 'database'>('system')
  const [testingProvider, setTestingProvider] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, any>>({})
  const [selectedModels, setSelectedModels] = useState<Record<string, string>>({})
  const [editingProvider, setEditingProvider] = useState<any>(null)
  const [configModalOpen, setConfigModalOpen] = useState(false)

  useEffect(() => {
    loadSystemInfo()
  }, [])

  useEffect(() => {
    // Initialize selected models from config
    if (llmConfig?.providers) {
      const models: Record<string, string> = {}
      llmConfig.providers.forEach((provider: any) => {
        if (provider.models && provider.models.length > 0) {
          models[provider.name] = provider.models[0]
        }
      })
      setSelectedModels(models)
    }
  }, [llmConfig])

  const loadSystemInfo = async () => {
    setLoading(true)
    try {
      const [sysInfo, llmCfg, providersH, cacheS] = await Promise.all([
        adminApi.getSystemInfo(),
        adminApi.getLLMConfig(),
        adminApi.checkProvidersHealth(),
        adminApi.getCacheStats(),
      ])

      setSystemInfo(sysInfo)
      setLLMConfig(llmCfg)
      setProvidersHealth(providersH)
      setCacheStats(cacheS)
    } catch (error) {
      console.error('Failed to load system info:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleClearCache = async () => {
    try {
      await adminApi.clearCache()
      loadSystemInfo()
    } catch (error) {
      console.error('Failed to clear cache:', error)
    }
  }

  const handleTestProvider = async (providerName: string, model?: string) => {
    setTestingProvider(providerName)
    try {
      const result = await adminApi.testAgent({
        task: 'Тестовая задача: выведи "Hello from DevOps Agent"',
        auto_approve: true,
      })
      
      setTestResults({
        ...testResults,
        [providerName]: {
          success: result.status === 'success',
          message: result.error || 'Провайдер работает корректно',
          timestamp: new Date().toISOString(),
          execution_time: result.execution_time,
        }
      })
    } catch (error: any) {
      setTestResults({
        ...testResults,
        [providerName]: {
          success: false,
          message: error.message || 'Ошибка при тестировании',
          timestamp: new Date().toISOString(),
        }
      })
    } finally {
      setTestingProvider(null)
    }
  }

  const handleEditProvider = (provider: any) => {
    setEditingProvider(provider)
    setConfigModalOpen(true)
  }

  const handleConfigSaved = () => {
    setConfigModalOpen(false)
    setEditingProvider(null)
    // Reload system info
    loadSystemInfo()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Settings className="h-6 w-6 text-gray-700" />
            <h1 className="text-2xl font-bold text-gray-900">Настройки системы</h1>
          </div>
          <button
            onClick={loadSystemInfo}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Обновить</span>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex space-x-4 mt-4">
          <button
            onClick={() => setActiveTab('system')}
            className={`px-4 py-2 rounded-lg font-medium ${
              activeTab === 'system'
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Система
          </button>
          <button
            onClick={() => setActiveTab('llm')}
            className={`px-4 py-2 rounded-lg font-medium ${
              activeTab === 'llm'
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            LLM Провайдеры
          </button>
          <button
            onClick={() => setActiveTab('cache')}
            className={`px-4 py-2 rounded-lg font-medium ${
              activeTab === 'cache'
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Кеш
          </button>
          <button
            onClick={() => setActiveTab('database')}
            className={`px-4 py-2 rounded-lg font-medium ${
              activeTab === 'database'
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            База данных
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'system' && (
          <div className="space-y-6">
            {/* Version */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Информация о системе</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Версия</p>
                  <p className="text-lg font-medium">{systemInfo?.version}</p>
                </div>
              </div>
            </div>

            {/* Components Status */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Статус компонентов</h2>
              <div className="space-y-4">
                {/* LLM Providers */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-3">
                      <Cpu className="h-5 w-5 text-gray-600" />
                      <div>
                        <p className="font-medium">LLM Провайдеры</p>
                        <p className="text-sm text-gray-600">
                          {systemInfo?.components.llm_providers.healthy.length} / {systemInfo?.components.llm_providers.available.length} доступно
                        </p>
                      </div>
                    </div>
                    {systemInfo?.components.llm_providers.healthy.length! > 0 ? (
                      <CheckCircle className="h-6 w-6 text-green-500" />
                    ) : (
                      <XCircle className="h-6 w-6 text-red-500" />
                    )}
                  </div>
                  {systemInfo?.components.llm_providers.healthy.length === 0 && (
                    <div className="mt-2 p-2 bg-red-50 rounded border border-red-200">
                      <p className="text-sm text-red-700">
                        <strong>Проблема:</strong> Нет доступных LLM провайдеров. Проверьте настройки API ключей во вкладке "LLM Провайдеры".
                      </p>
                    </div>
                  )}
                  {systemInfo?.components.llm_providers.available && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {systemInfo.components.llm_providers.available.map((provider) => (
                        <span
                          key={provider}
                          className={`px-2 py-1 text-xs rounded ${
                            systemInfo.components.llm_providers.healthy.includes(provider)
                              ? 'bg-green-100 text-green-700'
                              : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {provider}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Redis */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-3">
                      <Server className="h-5 w-5 text-gray-600" />
                      <div>
                        <p className="font-medium">Redis</p>
                        <p className="text-sm text-gray-600">
                          {systemInfo?.components.redis.enabled ? 'Включен' : 'Отключен'}
                        </p>
                      </div>
                    </div>
                    {systemInfo?.components.redis.healthy ? (
                      <CheckCircle className="h-6 w-6 text-green-500" />
                    ) : systemInfo?.components.redis.enabled ? (
                      <XCircle className="h-6 w-6 text-red-500" />
                    ) : (
                      <AlertCircle className="h-6 w-6 text-gray-400" />
                    )}
                  </div>
                  {systemInfo?.components.redis.enabled && !systemInfo?.components.redis.healthy && (
                    <div className="mt-2 p-2 bg-yellow-50 rounded border border-yellow-200">
                      <p className="text-sm text-yellow-700">
                        <strong>Внимание:</strong> Redis включен, но недоступен. Функции кеширования и управления сессиями могут не работать.
                      </p>
                    </div>
                  )}
                  {systemInfo?.components.redis.healthy && (
                    <div className="mt-2 p-2 bg-green-50 rounded">
                      <p className="text-sm text-green-700">
                        Функции: Кеширование LLM, Управление сессиями, Rate Limiting
                      </p>
                    </div>
                  )}
                </div>

                {/* Database */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-3">
                      <Database className="h-5 w-5 text-gray-600" />
                      <div>
                        <p className="font-medium">База данных PostgreSQL</p>
                        <p className="text-sm text-gray-600">
                          {systemInfo?.components.database.enabled ? 'Включена' : 'Отключена'}
                        </p>
                      </div>
                    </div>
                    {systemInfo?.components.database.healthy ? (
                      <CheckCircle className="h-6 w-6 text-green-500" />
                    ) : systemInfo?.components.database.enabled ? (
                      <XCircle className="h-6 w-6 text-red-500" />
                    ) : (
                      <AlertCircle className="h-6 w-6 text-gray-400" />
                    )}
                  </div>
                  {systemInfo?.components.database.enabled && !systemInfo?.components.database.healthy && (
                    <div className="mt-2 p-2 bg-yellow-50 rounded border border-yellow-200">
                      <p className="text-sm text-yellow-700">
                        <strong>Внимание:</strong> База данных включена, но недоступна. История задач и аудит логи не сохраняются.
                      </p>
                      <div className="mt-2">
                        <p className="text-xs text-gray-600">Для запуска PostgreSQL:</p>
                        <code className="text-xs bg-white p-1 rounded block mt-1">
                          docker-compose -f docker-compose.dev.yml up -d postgres
                        </code>
                      </div>
                    </div>
                  )}
                  {systemInfo?.components.database.healthy && (
                    <div className="mt-2 p-2 bg-green-50 rounded">
                      <p className="text-sm text-green-700">
                        Функции: История задач, Аудит логи, Сохранение окружений
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Features */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Включенные функции</h2>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(systemInfo?.features || {}).map(([feature, enabled]) => (
                  <div key={feature} className="flex items-center space-x-2 p-3 bg-gray-50 rounded">
                    {enabled ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-gray-400" />
                    )}
                    <span className="text-sm">{feature.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'llm' && (
          <div className="space-y-6">
            {/* Providers Health */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Статус провайдеров</h2>
              
              {providersHealth?.providers && providersHealth.providers.length > 0 ? (
                <div className="space-y-3">
                  {providersHealth.providers.map((provider: any) => (
                    <div key={provider.name} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium">{provider.name}</p>
                        <p className="text-sm text-gray-600">{provider.status}</p>
                      </div>
                      {provider.healthy ? (
                        <CheckCircle className="h-6 w-6 text-green-500" />
                      ) : (
                        <XCircle className="h-6 w-6 text-red-500" />
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center space-x-2 p-4 bg-yellow-50 rounded-lg">
                  <AlertCircle className="h-5 w-5 text-yellow-600" />
                  <p className="text-sm text-yellow-800">Нет доступных провайдеров для проверки</p>
                </div>
              )}
            </div>

            {/* LLM Configuration & Testing */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Конфигурация и тестирование провайдеров</h2>
              <div className="space-y-4">
                {llmConfig?.providers?.map((provider: any) => {
                  const isHealthy = providersHealth?.providers?.find((p: any) => p.name === provider.name)?.healthy
                  const testResult = testResults[provider.name]
                  
                  // Get models from provider or from global available_models
                  const providerModels = provider.models || llmConfig?.available_models?.[provider.name] || []
                  const providerWithModels = { ...provider, models: providerModels }
                  
                  return (
                    <div key={provider.name} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          <h3 className="font-medium text-lg">{provider.name}</h3>
                          {isHealthy ? (
                            <CheckCircle className="h-5 w-5 text-green-500" />
                          ) : (
                            <XCircle className="h-5 w-5 text-red-500" />
                          )}
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                          provider.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                        }`}>
                          {provider.enabled ? 'Включен' : 'Отключен'}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-3 text-sm mb-3">
                        <div>
                          <span className="text-gray-600">Тип:</span>
                          <span className="ml-2 font-medium">{provider.type}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Приоритет:</span>
                          <span className="ml-2 font-medium">{provider.priority}</span>
                        </div>
                      </div>

                      {/* Model Selection */}
                      {providerModels && providerModels.length > 0 && (
                        <div className="mb-3">
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Выбор модели:
                          </label>
                          <select
                            value={selectedModels[provider.name] || providerModels[0]}
                            onChange={(e) => setSelectedModels({...selectedModels, [provider.name]: e.target.value})}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            {providerModels.map((model: string) => (
                              <option key={model} value={model}>{model}</option>
                            ))}
                          </select>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex items-center justify-between pt-3 border-t gap-3">
                        <button
                          onClick={() => handleEditProvider(providerWithModels)}
                          className="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                        >
                          <Edit className="h-4 w-4" />
                          <span>Настроить</span>
                        </button>

                        <button
                          onClick={() => handleTestProvider(provider.name, selectedModels[provider.name])}
                          disabled={testingProvider === provider.name || !provider.enabled}
                          className={`flex items-center space-x-2 px-4 py-2 rounded-lg ${
                            provider.enabled
                              ? 'bg-blue-500 text-white hover:bg-blue-600'
                              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          }`}
                        >
                          {testingProvider === provider.name ? (
                            <>
                              <RefreshCw className="h-4 w-4 animate-spin" />
                              <span>Тестирование...</span>
                            </>
                          ) : (
                            <>
                              <Play className="h-4 w-4" />
                              <span>Протестировать</span>
                            </>
                          )}
                        </button>

                        {testResult && (
                          <div className={`flex items-center space-x-2 ${
                            testResult.success ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {testResult.success ? (
                              <CheckCircle className="h-5 w-5" />
                            ) : (
                              <XCircle className="h-5 w-5" />
                            )}
                            <span className="text-sm font-medium">
                              {testResult.success ? 'Работает' : 'Ошибка'}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Test Result Details */}
                      {testResult && (
                        <div className={`mt-3 p-3 rounded ${
                          testResult.success ? 'bg-green-50' : 'bg-red-50'
                        }`}>
                          <p className="text-sm text-gray-700">{testResult.message}</p>
                          {testResult.execution_time && (
                            <p className="text-xs text-gray-600 mt-1">
                              Время выполнения: {testResult.execution_time.toFixed(2)}s
                            </p>
                          )}
                        </div>
                      )}

                      {/* API Key Status */}
                      {provider.type === 'gemini' && (
                        <div className="mt-3 pt-3 border-t">
                          <div className="flex items-center space-x-2">
                            <Key className="h-4 w-4 text-gray-500" />
                            <span className="text-sm text-gray-600">
                              API ключ: {isHealthy ? 'Настроен' : 'Не настроен или недействителен'}
                            </span>
                          </div>
                          {!isHealthy && (
                            <div className="mt-2 p-3 bg-yellow-50 rounded">
                              <p className="text-sm text-yellow-800">
                                <strong>Инструкция:</strong> Установите переменную окружения GEMINI_API_KEY
                              </p>
                              <code className="text-xs text-gray-700 block mt-1">
                                export GEMINI_API_KEY=&quot;your-api-key-here&quot;
                              </code>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'cache' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Статистика кеша</h2>
                <button
                  onClick={handleClearCache}
                  className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                >
                  Очистить кеш
                </button>
              </div>

              {cacheStats?.enabled ? (
                <div>
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <p className="text-sm text-gray-600">Статус</p>
                      <p className="text-2xl font-bold text-blue-600">Включен</p>
                    </div>
                    <div className="p-4 bg-green-50 rounded-lg">
                      <p className="text-sm text-gray-600">Попадания</p>
                      <p className="text-2xl font-bold text-green-600">
                        {cacheStats?.stats?.hits || 0}
                      </p>
                    </div>
                    <div className="p-4 bg-orange-50 rounded-lg">
                      <p className="text-sm text-gray-600">Промахи</p>
                      <p className="text-2xl font-bold text-orange-600">
                        {cacheStats?.stats?.misses || 0}
                      </p>
                    </div>
                  </div>

                  {cacheStats?.stats && (
                    <div className="text-sm text-gray-600">
                      <pre className="bg-gray-50 p-4 rounded overflow-auto">
                        {JSON.stringify(cacheStats.stats, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-gray-600">Кеш отключен</p>
              )}
            </div>
          </div>
        )}

        {activeTab === 'database' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Статус базы данных</h2>
              <div className="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg">
                <Database className="h-8 w-8 text-gray-600" />
                <div>
                  <p className="font-medium">PostgreSQL</p>
                  <p className="text-sm text-gray-600">
                    {systemInfo?.components.database.healthy ? 'Подключена' : 'Не подключена'}
                  </p>
                </div>
                {systemInfo?.components.database.healthy ? (
                  <CheckCircle className="h-6 w-6 text-green-500 ml-auto" />
                ) : (
                  <XCircle className="h-6 w-6 text-red-500 ml-auto" />
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Provider Config Modal */}
      <ProviderConfigModal
        provider={editingProvider}
        isOpen={configModalOpen}
        onClose={() => {
          setConfigModalOpen(false)
          setEditingProvider(null)
        }}
        onSave={handleConfigSaved}
      />
    </div>
  )
}
