'use client'

import { useState, useEffect } from 'react'
import { X, Save, Key, Settings, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { adminApi } from '@/lib/api'

interface ProviderConfigModalProps {
  provider: any
  isOpen: boolean
  onClose: () => void
  onSave: () => void
}

export function ProviderConfigModal({ provider, isOpen, onClose, onSave }: ProviderConfigModalProps) {
  const [apiKey, setApiKey] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [enabled, setEnabled] = useState(true)
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(4096)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (provider) {
      // Use models from provider or fallback to empty array
      const models = provider.models || []
      setSelectedModel(provider.current_model || (models.length > 0 ? models[0] : ''))
      setEnabled(provider.enabled)
      setTemperature(0.7)
      setMaxTokens(4096)
      setTestResult(null)
      setError('')
    }
  }, [provider])

  if (!isOpen || !provider) return null

  const handleSave = async () => {
    setSaving(true)
    setError('')
    
    try {
      const config: any = {
        model: selectedModel,
        enabled: enabled,
      }

      // Only send API key if it's changed (not empty)
      if (apiKey) {
        config.api_key = apiKey
      }

      if (temperature !== undefined) {
        config.temperature = temperature
      }

      if (maxTokens !== undefined) {
        config.max_tokens = maxTokens
      }

      const result = await adminApi.updateProviderConfig(provider.name, config)
      
      if (result.success) {
        // Test the configuration
        await handleTest()
        onSave()
      } else {
        setError('Не удалось сохранить конфигурацию')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Ошибка при сохранении')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    
    try {
      const result = await adminApi.testProviderWithConfig(provider.name, selectedModel)
      setTestResult(result)
    } catch (err: any) {
      setTestResult({
        success: false,
        error: err.response?.data?.detail || err.message || 'Ошибка при тестировании'
      })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <Settings className="h-6 w-6 text-blue-600" />
            <div>
              <h2 className="text-xl font-bold">Настройка {provider.name}</h2>
              <p className="text-sm text-gray-600">Тип: {provider.type}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* API Key */}
          {provider.type === 'gemini' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Key className="h-4 w-4 inline mr-2" />
                API Ключ
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={provider.has_api_key ? "Введите новый ключ для изменения" : "Введите API ключ"}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {provider.has_api_key && (
                <p className="text-xs text-green-600 mt-1">
                  ✓ API ключ уже настроен
                </p>
              )}
              {!provider.has_api_key && (
                <p className="text-xs text-red-600 mt-1">
                  ⚠ API ключ не настроен
                </p>
              )}
            </div>
          )}

          {/* Model Selection */}
          {provider.models && provider.models.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Модель
              </label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {provider.models.map((model: string) => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
              <p className="text-xs text-gray-600 mt-1">
                Текущая модель: {provider.current_model || 'не установлена'}
              </p>
            </div>
          )}

          {/* Temperature */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Temperature: {temperature}
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-600">
              <span>Более детерминированный</span>
              <span>Более креативный</span>
            </div>
          </div>

          {/* Max Tokens */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Максимум токенов
            </label>
            <input
              type="number"
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value))}
              min="256"
              max="32768"
              step="256"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Enabled */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium">Включить провайдер</p>
              <p className="text-sm text-gray-600">Разрешить использование этого провайдера</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          {/* Test Result */}
          {testResult && (
            <div className={`p-4 rounded-lg ${
              testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
            }`}>
              <div className="flex items-start space-x-3">
                {testResult.success ? (
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className={`font-medium ${
                    testResult.success ? 'text-green-800' : 'text-red-800'
                  }`}>
                    {testResult.success ? 'Тест пройден успешно!' : 'Тест не пройден'}
                  </p>
                  {testResult.success && testResult.response && (
                    <p className="text-sm text-green-700 mt-1">
                      Ответ: {testResult.response}
                    </p>
                  )}
                  {testResult.success && testResult.execution_time && (
                    <p className="text-xs text-green-600 mt-1">
                      Время выполнения: {testResult.execution_time.toFixed(2)}s
                    </p>
                  )}
                  {!testResult.success && testResult.error && (
                    <p className="text-sm text-red-700 mt-1">
                      Ошибка: {testResult.error}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start space-x-2 p-4 bg-red-50 rounded-lg border border-red-200">
              <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t bg-gray-50">
          <button
            onClick={handleTest}
            disabled={testing || saving}
            className="px-4 py-2 text-blue-600 border border-blue-600 rounded-lg hover:bg-blue-50 disabled:opacity-50"
          >
            {testing ? 'Тестирование...' : 'Тестировать'}
          </button>
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Отмена
          </button>
          <button
            onClick={handleSave}
            disabled={saving || testing}
            className="flex items-center space-x-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            <span>{saving ? 'Сохранение...' : 'Сохранить'}</span>
          </button>
        </div>
      </div>
    </div>
  )
}
