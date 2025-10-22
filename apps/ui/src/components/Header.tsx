'use client'

import { useState } from 'react'
import { Menu, Bell, User, Server } from 'lucide-react'
import { Environment } from '@/types/environment'
import { EnvironmentSelector } from './EnvironmentSelector'

interface HeaderProps {
  onMenuClick: () => void
  selectedEnvironment: Environment | null
  onEnvironmentChange: (environment: Environment) => void
}

export function Header({ onMenuClick, selectedEnvironment, onEnvironmentChange }: HeaderProps) {
  const [showEnvironmentSelector, setShowEnvironmentSelector] = useState(false)

  return (
    <header className="relative border-b border-slate-100 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/70">
      <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          {/* Left section */}
          <div className="flex items-center gap-3">
            <button
              onClick={onMenuClick}
              className="rounded-xl border border-slate-200 p-2 text-slate-600 transition hover:bg-slate-100 lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-lg font-semibold text-slate-900">DevOps LLM Agent</h1>
              <p className="text-xs text-slate-500">Интеллектуальный помощник инженера</p>
            </div>
          </div>

          {/* Center section */}
          <div className="hidden max-w-lg flex-1 px-8 lg:block">
            <button
              onClick={() => setShowEnvironmentSelector(true)}
              className="flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left shadow-sm transition hover:border-indigo-200 hover:shadow"
            >
              <div className="flex items-center gap-3">
                <span className="rounded-xl bg-indigo-100 p-2 text-indigo-600">
                  <Server className="h-5 w-5" />
                </span>
                <div className="leading-tight">
                  {selectedEnvironment ? (
                    <>
                      <p className="text-sm font-medium text-slate-900">
                        {selectedEnvironment.display_name}
                      </p>
                      <p className="text-xs text-slate-500">
                        Тип: {selectedEnvironment.type}{' '}
                        {selectedEnvironment.metadata?.region
                          ? `• Регион: ${selectedEnvironment.metadata.region}`
                          : ''}
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="text-sm font-medium text-slate-900">
                        Выберите окружение
                      </p>
                      <p className="text-xs text-slate-500">
                        Нажмите, чтобы выбрать сервер или кластер
                      </p>
                    </>
                  )}
                </div>
              </div>
              <span className="text-xs font-medium text-indigo-500">изменить</span>
            </button>
          </div>

          {/* Right section */}
          <div className="flex items-center gap-2">
            <button className="rounded-xl border border-slate-200 p-2 text-slate-500 transition hover:bg-slate-100">
              <Bell className="h-5 w-5" />
            </button>
            <button className="rounded-xl border border-slate-200 p-2 text-slate-500 transition hover:bg-slate-100">
              <User className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Environment Selector Modal */}
      {showEnvironmentSelector && (
        <EnvironmentSelector
          selectedEnvironment={selectedEnvironment}
          onEnvironmentChange={onEnvironmentChange}
          onClose={() => setShowEnvironmentSelector(false)}
        />
      )}
    </header>
  )
}

