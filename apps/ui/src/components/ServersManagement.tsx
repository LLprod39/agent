/**
 * Servers Management Component - управление SSH серверами
 */

'use client';

import React, { useState, useEffect } from 'react';

interface Server {
  id: string;
  name: string;
  host: string;
  port: number;
  username: string;
  authType: 'password' | 'key';
  keyPath?: string;
  bastion?: string;
  status: 'online' | 'offline' | 'testing' | 'unknown';
  lastCheck?: string;
  environment: 'development' | 'staging' | 'production';
}

interface ServerFormData {
  name: string;
  host: string;
  port: number;
  username: string;
  authType: 'password' | 'key';
  password?: string;
  keyPath?: string;
  bastion?: string;
  environment: 'development' | 'staging' | 'production';
}

export const ServersManagement: React.FC = () => {
  const [servers, setServers] = useState<Server[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingServer, setEditingServer] = useState<Server | null>(null);
  const [testingServer, setTestingServer] = useState<string | null>(null);

  const [formData, setFormData] = useState<ServerFormData>({
    name: '',
    host: '',
    port: 22,
    username: '',
    authType: 'key',
    keyPath: '~/.ssh/id_rsa',
    environment: 'development',
  });

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      // В реальности будет API вызов
      const mockServers: Server[] = [
        {
          id: '1',
          name: 'Development VM',
          host: 'dev-vm-01.local',
          port: 22,
          username: 'admin',
          authType: 'key',
          keyPath: '~/.ssh/id_rsa',
          status: 'online',
          lastCheck: new Date().toISOString(),
          environment: 'development',
        },
        {
          id: '2',
          name: 'Staging Server',
          host: 'staging.example.com',
          port: 22,
          username: 'deploy',
          authType: 'key',
          bastion: 'bastion.example.com',
          status: 'unknown',
          environment: 'staging',
        },
        {
          id: '3',
          name: 'Production Web',
          host: 'prod-web-01.example.com',
          port: 22,
          username: 'root',
          authType: 'key',
          bastion: 'bastion-prod.example.com',
          status: 'offline',
          lastCheck: new Date(Date.now() - 3600000).toISOString(),
          environment: 'production',
        },
      ];
      setServers(mockServers);
    } catch (error) {
      console.error('Failed to load servers:', error);
    }
  };

  const handleTestConnection = async (serverId: string) => {
    setTestingServer(serverId);

    try {
      // Имитация тестирования подключения
      await new Promise(resolve => setTimeout(resolve, 2000));

      setServers(prev =>
        prev.map(server =>
          server.id === serverId
            ? { ...server, status: 'online', lastCheck: new Date().toISOString() }
            : server
        )
      );
    } catch (error) {
      setServers(prev =>
        prev.map(server =>
          server.id === serverId
            ? { ...server, status: 'offline', lastCheck: new Date().toISOString() }
            : server
        )
      );
    } finally {
      setTestingServer(null);
    }
  };

  const handleAddServer = async (e: React.FormEvent) => {
    e.preventDefault();

    const newServer: Server = {
      id: Date.now().toString(),
      name: formData.name,
      host: formData.host,
      port: formData.port,
      username: formData.username,
      authType: formData.authType,
      keyPath: formData.keyPath,
      bastion: formData.bastion,
      status: 'unknown',
      environment: formData.environment,
    };

    setServers([...servers, newServer]);
    setShowAddForm(false);
    resetForm();
  };

  const handleEditServer = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!editingServer) return;

    setServers(prev =>
      prev.map(server =>
        server.id === editingServer.id
          ? { ...server, ...formData }
          : server
      )
    );

    setEditingServer(null);
    resetForm();
  };

  const handleDeleteServer = async (serverId: string) => {
    if (window.confirm('Вы уверены что хотите удалить этот сервер?')) {
      setServers(prev => prev.filter(s => s.id !== serverId));
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      host: '',
      port: 22,
      username: '',
      authType: 'key',
      keyPath: '~/.ssh/id_rsa',
      environment: 'development',
    });
  };

  const startEdit = (server: Server) => {
    setEditingServer(server);
    setFormData({
      name: server.name,
      host: server.host,
      port: server.port,
      username: server.username,
      authType: server.authType,
      keyPath: server.keyPath,
      bastion: server.bastion,
      environment: server.environment,
    });
    setShowAddForm(true);
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      online: 'bg-green-100 text-green-800 border-green-200',
      offline: 'bg-red-100 text-red-800 border-red-200',
      testing: 'bg-blue-100 text-blue-800 border-blue-200',
      unknown: 'bg-gray-100 text-gray-800 border-gray-200',
    };

    const icons = {
      online: '✓',
      offline: '✗',
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

  const getEnvironmentBadge = (env: string) => {
    const colors = {
      production: 'bg-red-50 text-red-700 border-red-200',
      staging: 'bg-yellow-50 text-yellow-700 border-yellow-200',
      development: 'bg-blue-50 text-blue-700 border-blue-200',
    };

    return (
      <span
        className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${
          colors[env as keyof typeof colors] || 'bg-gray-50 text-gray-700 border-gray-200'
        }`}
      >
        {env.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Серверы</h1>
            <p className="text-gray-600 mt-1">Управление SSH подключениями</p>
          </div>
          <button
            onClick={() => {
              setShowAddForm(true);
              setEditingServer(null);
              resetForm();
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            <span>Добавить Сервер</span>
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4">
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
            <div className="text-sm text-gray-600">Всего серверов</div>
            <div className="text-2xl font-bold text-gray-900">{servers.length}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
            <div className="text-sm text-gray-600">Онлайн</div>
            <div className="text-2xl font-bold text-green-600">
              {servers.filter(s => s.status === 'online').length}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
            <div className="text-sm text-gray-600">Офлайн</div>
            <div className="text-2xl font-bold text-red-600">
              {servers.filter(s => s.status === 'offline').length}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-gray-500">
            <div className="text-sm text-gray-600">Не проверено</div>
            <div className="text-2xl font-bold text-gray-600">
              {servers.filter(s => s.status === 'unknown').length}
            </div>
          </div>
        </div>
      </div>

      {/* Add/Edit Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6 border-2 border-blue-200">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            {editingServer ? 'Редактировать Сервер' : 'Добавить Сервер'}
          </h2>
          <form onSubmit={editingServer ? handleEditServer : handleAddServer} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Название
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="Development VM"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Окружение
                </label>
                <select
                  value={formData.environment}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      environment: e.target.value as any,
                    })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="development">Development</option>
                  <option value="staging">Staging</option>
                  <option value="production">Production</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Host</label>
                <input
                  type="text"
                  value={formData.host}
                  onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="server.example.com"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Port</label>
                <input
                  type="number"
                  value={formData.port}
                  onChange={(e) =>
                    setFormData({ ...formData, port: parseInt(e.target.value) })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  min="1"
                  max="65535"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="admin"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Тип Авторизации
                </label>
                <select
                  value={formData.authType}
                  onChange={(e) =>
                    setFormData({ ...formData, authType: e.target.value as any })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="key">SSH Key</option>
                  <option value="password">Password</option>
                </select>
              </div>

              {formData.authType === 'key' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Путь к ключу
                  </label>
                  <input
                    type="text"
                    value={formData.keyPath}
                    onChange={(e) => setFormData({ ...formData, keyPath: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="~/.ssh/id_rsa"
                  />
                </div>
              )}

              {formData.authType === 'password' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Пароль
                  </label>
                  <input
                    type="password"
                    value={formData.password || ''}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    placeholder="••••••••"
                  />
                </div>
              )}

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Bastion Host (опционально)
                </label>
                <input
                  type="text"
                  value={formData.bastion || ''}
                  onChange={(e) => setFormData({ ...formData, bastion: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="bastion.example.com"
                />
              </div>
            </div>

            <div className="flex space-x-3">
              <button
                type="submit"
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                {editingServer ? 'Сохранить' : 'Добавить'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowAddForm(false);
                  setEditingServer(null);
                  resetForm();
                }}
                className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Servers List */}
      <div className="bg-white rounded-lg shadow">
        <div className="divide-y divide-gray-200">
          {servers.length === 0 ? (
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
                  d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"
                />
              </svg>
              <p className="text-lg font-medium">Нет серверов</p>
              <p className="text-sm mt-1">Добавьте первый сервер для начала работы</p>
            </div>
          ) : (
            servers.map((server) => (
              <div key={server.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">{server.name}</h3>
                      {getStatusBadge(testingServer === server.id ? 'testing' : server.status)}
                      {getEnvironmentBadge(server.environment)}
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-gray-600">
                      <div>
                        <span className="font-medium">Host:</span> {server.host}:{server.port}
                      </div>
                      <div>
                        <span className="font-medium">User:</span> {server.username}
                      </div>
                      <div>
                        <span className="font-medium">Auth:</span> {server.authType === 'key' ? 'SSH Key' : 'Password'}
                      </div>
                      {server.bastion && (
                        <div>
                          <span className="font-medium">Bastion:</span> {server.bastion}
                        </div>
                      )}
                    </div>

                    {server.lastCheck && (
                      <div className="text-xs text-gray-500 mt-1">
                        Последняя проверка: {new Date(server.lastCheck).toLocaleString()}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-2 ml-4">
                    <button
                      onClick={() => handleTestConnection(server.id)}
                      disabled={testingServer === server.id}
                      className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {testingServer === server.id ? 'Тестирую...' : 'Тест'}
                    </button>
                    <button
                      onClick={() => startEdit(server)}
                      className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                    >
                      Изменить
                    </button>
                    <button
                      onClick={() => handleDeleteServer(server.id)}
                      className="px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default ServersManagement;
