/**
 * Main Application Layout with Navigation
 */

'use client';

import React, { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';

interface AppLayoutProps {
  children: React.ReactNode;
}

interface NavItem {
  id: string;
  name: string;
  icon: string;
  path: string;
  badge?: number;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const navItems: NavItem[] = [
    { id: 'dashboard', name: 'Dashboard', icon: '📊', path: '/dashboard' },
    { id: 'tasks', name: 'Задачи', icon: '📋', path: '/tasks' },
    { id: 'terminal', name: 'Терминал', icon: '💻', path: '/terminal' },
    { id: 'servers', name: 'Серверы', icon: '🖥️', path: '/servers' },
    { id: 'providers', name: 'Провайдеры', icon: '🤖', path: '/providers' },
    { id: 'settings', name: 'Настройки', icon: '⚙️', path: '/settings' },
  ];

  const handleNavigation = (path: string) => {
    router.push(path);
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    router.push('/login');
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } bg-gray-900 text-white transition-all duration-300 flex flex-col`}
      >
        {/* Logo */}
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center justify-between">
            {sidebarOpen ? (
              <div>
                <h1 className="text-xl font-bold">🤖 DevOps Agent</h1>
                <p className="text-xs text-gray-400 mt-1">AI для Linux серверов</p>
              </div>
            ) : (
              <div className="text-2xl mx-auto">🤖</div>
            )}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1 hover:bg-gray-800 rounded transition-colors"
            >
              {sidebarOpen ? '◀' : '▶'}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const isActive = pathname?.startsWith(item.path);
            return (
              <button
                key={item.id}
                onClick={() => handleNavigation(item.path)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <span className="text-xl">{item.icon}</span>
                {sidebarOpen && (
                  <>
                    <span className="flex-1 text-left font-medium">{item.name}</span>
                    {item.badge && (
                      <span className="px-2 py-1 bg-red-500 text-white text-xs rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </button>
            );
          })}
        </nav>

        {/* User Menu */}
        <div className="p-4 border-t border-gray-800">
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="w-full flex items-center space-x-3 px-4 py-3 rounded-lg hover:bg-gray-800 transition-colors"
            >
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center font-bold">
                A
              </div>
              {sidebarOpen && (
                <div className="flex-1 text-left">
                  <div className="font-medium">Admin</div>
                  <div className="text-xs text-gray-400">admin@devops.local</div>
                </div>
              )}
            </button>

            {/* Dropdown */}
            {userMenuOpen && sidebarOpen && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-gray-800 rounded-lg shadow-lg py-2">
                <button
                  onClick={() => handleNavigation('/profile')}
                  className="w-full px-4 py-2 text-left hover:bg-gray-700 transition-colors flex items-center space-x-2"
                >
                  <span>👤</span>
                  <span>Профиль</span>
                </button>
                <button
                  onClick={() => handleNavigation('/settings')}
                  className="w-full px-4 py-2 text-left hover:bg-gray-700 transition-colors flex items-center space-x-2"
                >
                  <span>⚙️</span>
                  <span>Настройки</span>
                </button>
                <div className="border-t border-gray-700 my-2"></div>
                <button
                  onClick={handleLogout}
                  className="w-full px-4 py-2 text-left hover:bg-gray-700 transition-colors flex items-center space-x-2 text-red-400"
                >
                  <span>🚪</span>
                  <span>Выход</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="bg-white shadow-sm z-10">
          <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center space-x-4">
              <h2 className="text-2xl font-bold text-gray-800">
                {navItems.find((item) => pathname?.startsWith(item.path))?.name || 'DevOps Agent'}
              </h2>
            </div>

            <div className="flex items-center space-x-4">
              {/* Quick Actions */}
              <button
                onClick={() => handleNavigation('/tasks/new')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
              >
                <span>+</span>
                <span>Новая Задача</span>
              </button>

              {/* Notifications */}
              <button className="relative p-2 text-gray-600 hover:text-gray-900 transition-colors">
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                  />
                </svg>
                <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full"></span>
              </button>

              {/* Help */}
              <button
                onClick={() => window.open('/docs', '_blank')}
                className="p-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto bg-gray-100">
          {children}
        </main>

        {/* Footer */}
        <footer className="bg-white border-t border-gray-200 px-6 py-3">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div>© 2025 DevOps Agent • AI-powered Linux management</div>
            <div className="flex items-center space-x-4">
              <span className="flex items-center space-x-2">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                <span>All Systems Operational</span>
              </span>
              <span>v1.0.0-beta</span>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default AppLayout;
