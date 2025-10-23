/**
 * LLM Providers Management - управление провайдерами LLM
 */

'use client';

import React, { useState, useEffect } from 'react';

interface Provider {
  id: string;
  name: string;
  type: 'gemini' | 'ollama' | 'local';
  enabled: boolean;
  priority: number;
  status: 'healthy' | 'unhealthy' | 'testing' | 'unknown';
  config: {
    api_key?: string;
    model?: string;
    base_url?: string;
    temperature?: number;
    max_tokens?: number;
  };
  lastCheck?: string;
  lastError?: string;
}

export const ProvidersManagement: React.FC = () => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [showApiKey, setShowApiKey] = useState<{ [key: string]: boolean }>({});

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    // Mock data - в реальности будет API вызов
    const mockProviders: Provider[] = [
      {
        id: '1',
        name: 'Gemini',
        type: 'gemini',
        enabled: true,
        priority: 100,
        status: 'unknown',
        config: {
          api_key: 'AIzaSyBdMFRLoZPNVPyqSZ2CL4SoQQ7_4PnRpW4',
          model: 'gemini-2.5-flash',
          temperature: 0.7,
          max_tokens: 4096,
        },
      },
      {
        id: '2',
        name: 'Ollama',
        type: 'ollama',
        enabled: false,
        priority: 50,
        status: 'unknown',
        config: {
          base_url: 'http://localhost:11434',
          model: 'llama3',
          temperature: 0.7,
        },
      },
      {
        id: '3',
        name: 'Local',
        type: 'local',
        enabled: true,
        priority: 10,
        status: 'healthy',
        config: {
          model: 'local-simulator',
        },
        lastCheck: new Date().toISOString(),
      },
    ];

    setProviders(mockProviders);
  };

  const handleTestProvider = async (providerId: string) => {
    setTestingProvider(providerId);

    try {
      // Имитация тестирования
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Случайный результат для демонстрации
      const isHealthy = Math.random() > 0.3;

      setProviders(prev =>
        prev.map(p =>
          p.id === providerId
            ? {
                ...p,
                status: isHealthy ? 'healthy' : 'unhealthy',
                lastCheck: new Date().toISOString(),
                lastError: isHealthy ? undefined : 'Connection failed: 403 Forbidden',
              }
            : p
        )
      );
    } catch (error) {
      setProviders(prev =>
        prev.map(p =>
          p.id === providerId
            ? {
                ...p,
                status: 'unhealthy',
                lastCheck: new Date().toISOString(),
                lastError: 'Test failed',
              }
            : p
        )
      );
    } finally {
      setTestingProvider(null);
    }
  };

  const handleToggleProvider = (providerId: string) => {
    setProviders(prev =>
      prev.map(p => (p.id === providerId ? { ...p, enabled: !p.enabled } : p))
    );
  };

  const handleSaveProvider = (provider: Provider) => {
    setProviders(prev => prev.map(p => (p.id === provider.id ? provider : p)));
    setEditingProvider(null);
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      healthy: 'bg-green-100 text-green-800 border-green-200',
      unhealthy: 'bg-red-100 text-red-800 border-red-200',
      testing: 'bg-blue-100 text-blue-800 border-blue-200',
      unknown: 'bg-gray-100 text-gray-800 border-gray-200',
    };

    const icons = {
      healthy: '✓',
      unhealthy: '✗',
      testing: '⟳',
      unknown: '?',
    };

    return (
      <span
        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${
          styles[status as keyof typeof styles] || styles.unknown
        }`}
      >
        <span className="mr-1">{icons[status as keyof typeof icons] || '?'}</span>
        {status.toUpperCase()}
      </span>
    );
  };

  const getProviderIcon = (type: string) => {
    switch (type) {
      case 'gemini':
        return '🤖';
      case 'ollama':
        return '🦙';
      case 'local':
        return '💻';
      default:
        return '🔧';
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">LLM Провайдеры</h1>
            <p className="text-gray-600 mt-1">Управление AI моделями и провайдерами</p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4">
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
            <div className="text-sm text-gray-600">Всего провайдеров</div>
            <div className="text-2xl font-bold text-gray-900">{providers.length}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
            <div className="text-sm text-gray-600">Активных</div>
            <div className="text-2xl font-bold text-green-600">
              {providers.filter(p => p.enabled).length}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-emerald-500">
            <div className="text-sm text-gray-600">Работают</div>
            <div className="text-2xl font-bold text-emerald-600">
              {providers.filter(p => p.status === 'healthy').length}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
            <div className="text-sm text-gray-600">Проблемы</div>
            <div className="text-2xl font-bold text-red-600">
              {providers.filter(p => p.status === 'unhealthy').length}
            </div>
          </div>
        </div>
      </div>

      {/* Providers List */}
      <div className="space-y-4">
        {providers.map((provider) => (
          <div key={provider.id} className="bg-white rounded-lg shadow-lg overflow-hidden">
            {/* Provider Header */}
            <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-white border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="text-4xl">{getProviderIcon(provider.type)}</div>
                  <div>
                    <div className="flex items-center space-x-3">
                      <h3 className="text-xl font-bold text-gray-900">{provider.name}</h3>
                      {getStatusBadge(
                        testingProvider === provider.id ? 'testing' : provider.status
                      )}
                      <span className="text-sm text-gray-500">
                        Priority: {provider.priority}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">
                      Type: {provider.type.toUpperCase()} • Model: {provider.config.model}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={provider.enabled}
                      onChange={() => handleToggleProvider(provider.id)}
                      className="sr-only peer"
                    />
                    <div className="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    <span className="ml-3 text-sm font-medium text-gray-900">
                      {provider.enabled ? 'Включен' : 'Выключен'}
                    </span>
                  </label>

                  <button
                    onClick={() => handleTestProvider(provider.id)}
                    disabled={testingProvider === provider.id || !provider.enabled}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {testingProvider === provider.id ? 'Тестирую...' : 'Тест'}
                  </button>

                  <button
                    onClick={() => setEditingProvider(provider)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                  >
                    Настроить
                  </button>
                </div>
              </div>
            </div>

            {/* Provider Details */}
            <div className="px-6 py-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Configuration */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Конфигурация</h4>
                  <div className="space-y-2 text-sm">
                    {provider.config.api_key && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">API Key:</span>
                        <div className="flex items-center space-x-2">
                          <code className="px-2 py-1 bg-gray-100 rounded font-mono text-xs">
                            {showApiKey[provider.id]
                              ? provider.config.api_key
                              : '••••••••••••••••'}
                          </code>
                          <button
                            onClick={() =>
                              setShowApiKey((prev) => ({
                                ...prev,
                                [provider.id]: !prev[provider.id],
                              }))
                            }
                            className="text-blue-600 hover:text-blue-700"
                          >
                            {showApiKey[provider.id] ? '🙈' : '👁️'}
                          </button>
                        </div>
                      </div>
                    )}

                    {provider.config.base_url && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Base URL:</span>
                        <code className="px-2 py-1 bg-gray-100 rounded font-mono text-xs">
                          {provider.config.base_url}
                        </code>
                      </div>
                    )}

                    {provider.config.temperature !== undefined && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Temperature:</span>
                        <span className="font-medium">{provider.config.temperature}</span>
                      </div>
                    )}

                    {provider.config.max_tokens && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Max Tokens:</span>
                        <span className="font-medium">{provider.config.max_tokens}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Status */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Статус</h4>
                  <div className="space-y-2 text-sm">
                    {provider.lastCheck && (
                      <div>
                        <span className="text-gray-600">Последняя проверка:</span>
                        <div className="text-gray-900 mt-1">
                          {new Date(provider.lastCheck).toLocaleString()}
                        </div>
                      </div>
                    )}

                    {provider.lastError && (
                      <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded">
                        <div className="text-xs font-semibold text-red-700 mb-1">
                          Последняя ошибка:
                        </div>
                        <div className="text-xs text-red-600">{provider.lastError}</div>
                      </div>
                    )}

                    {provider.status === 'healthy' && (
                      <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded">
                        <div className="text-xs text-green-700">
                          ✓ Провайдер работает нормально
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Edit Form */}
            {editingProvider?.id === provider.id && (
              <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
                <h4 className="text-lg font-semibold text-gray-900 mb-4">
                  Редактирование конфигурации
                </h4>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSaveProvider(editingProvider);
                  }}
                  className="space-y-4"
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Приоритет (чем выше, тем важнее)
                      </label>
                      <input
                        type="number"
                        value={editingProvider.priority}
                        onChange={(e) =>
                          setEditingProvider({
                            ...editingProvider,
                            priority: parseInt(e.target.value),
                          })
                        }
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        min="0"
                        max="1000"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Модель
                      </label>
                      <input
                        type="text"
                        value={editingProvider.config.model || ''}
                        onChange={(e) =>
                          setEditingProvider({
                            ...editingProvider,
                            config: { ...editingProvider.config, model: e.target.value },
                          })
                        }
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      />
                    </div>

                    {editingProvider.type === 'gemini' && (
                      <div className="md:col-span-2">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          API Key
                        </label>
                        <input
                          type="text"
                          value={editingProvider.config.api_key || ''}
                          onChange={(e) =>
                            setEditingProvider({
                              ...editingProvider,
                              config: { ...editingProvider.config, api_key: e.target.value },
                            })
                          }
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none font-mono text-sm"
                          placeholder="AIza..."
                        />
                      </div>
                    )}

                    {editingProvider.type === 'ollama' && (
                      <div className="md:col-span-2">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Base URL
                        </label>
                        <input
                          type="text"
                          value={editingProvider.config.base_url || ''}
                          onChange={(e) =>
                            setEditingProvider({
                              ...editingProvider,
                              config: { ...editingProvider.config, base_url: e.target.value },
                            })
                          }
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                          placeholder="http://localhost:11434"
                        />
                      </div>
                    )}

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Temperature (0.0 - 1.0)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                        value={editingProvider.config.temperature || 0.7}
                        onChange={(e) =>
                          setEditingProvider({
                            ...editingProvider,
                            config: {
                              ...editingProvider.config,
                              temperature: parseFloat(e.target.value),
                            },
                          })
                        }
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Max Tokens
                      </label>
                      <input
                        type="number"
                        value={editingProvider.config.max_tokens || 4096}
                        onChange={(e) =>
                          setEditingProvider({
                            ...editingProvider,
                            config: {
                              ...editingProvider.config,
                              max_tokens: parseInt(e.target.value),
                            },
                          })
                        }
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="flex space-x-3">
                    <button
                      type="submit"
                      className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                    >
                      Сохранить
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingProvider(null)}
                      className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                    >
                      Отмена
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Help Section */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">💡 Подсказки</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• <strong>Gemini</strong>: Требует API ключ от Google AI Studio</li>
          <li>• <strong>Ollama</strong>: Нужен локально установленный Ollama сервер</li>
          <li>• <strong>Local</strong>: Работает без настройки, но дает простые планы</li>
          <li>
            • Провайдеры с большим приоритетом используются в первую очередь
          </li>
          <li>• Отключенные провайдеры не будут использоваться</li>
        </ul>
      </div>
    </div>
  );
};

export default ProvidersManagement;
