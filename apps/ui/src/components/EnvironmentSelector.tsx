'use client'

import { useState, useEffect } from 'react'
import {
  X,
  Check,
  AlertCircle,
  Server,
  Network,
  Boxes,
  Cpu,
  Cloud,
} from 'lucide-react'
import { Environment } from '@/types/environment'
import { environmentApi } from '@/lib/api'

interface EnvironmentSelectorProps {
  selectedEnvironment: Environment | null
  onEnvironmentChange: (environment: Environment) => void
  onClose: () => void
}

const typeIconMap: Record<string, JSX.Element> = {
  k8s: <Network className="h-5 w-5" />,
  vm: <Server className="h-5 w-5" />,
  docker: <Boxes className="h-5 w-5" />,
  'bare-metal': <Cpu className="h-5 w-5" />,
  serverless: <Cloud className="h-5 w-5" />,
}

const riskBadge = (risk?: string) => {
  switch (risk) {
    case 'high':
      return 'bg-rose-100 text-rose-700'
    case 'medium':
      return 'bg-amber-100 text-amber-700'
    case 'low':
    default:
      return 'bg-emerald-100 text-emerald-700'
  }
}

export function EnvironmentSelector({
  selectedEnvironment,
  onEnvironmentChange,
  onClose,
}: EnvironmentSelectorProps) {
  const [environments, setEnvironments] = useState<Environment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadEnvironments()
  }, [])

  const loadEnvironments = async () => {
    try {
      setLoading(true)
      const response = await environmentApi.listEnvironments()
      setEnvironments(response.environments)
      setError(null)
    } catch (err) {
      setError('Не удалось загрузить список окружений. Попробуйте ещё раз.')
      console.error('Error loading environments:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleEnvironmentSelect = (environment: Environment) => {
    onEnvironmentChange(environment)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-3xl overflow-hidden rounded-3xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Выбор окружения</h2>
            <p className="text-xs text-slate-500">
              Выберите сервер или кластер, в котором агент будет выполнять команды.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto px-6 py-5">
          {loading ? (
            <div className="py-12 text-center">
              <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
              <p className="mt-4 text-sm text-slate-500">Загружаем окружения…</p>
            </div>
          ) : error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-5 py-6 text-center">
              <AlertCircle className="mx-auto mb-3 h-6 w-6 text-rose-500" />
              <p className="text-sm text-rose-600">{error}</p>
              <button
                onClick={loadEnvironments}
                className="mt-4 inline-flex items-center rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
              >
                Повторить
              </button>
            </div>
          ) : environments.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-5 py-8 text-center text-sm text-slate-500">
              Нет доступных профилей окружений.
            </div>
          ) : (
            <div className="grid gap-4">
              {environments.map((environment) => {
                const isSelected = selectedEnvironment?.id === environment.id
                return (
                  <button
                    key={environment.id}
                    onClick={() => handleEnvironmentSelect(environment)}
                    className={`flex w-full items-start justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left shadow-sm transition hover:border-indigo-200 hover:shadow ${
                      isSelected ? 'ring-2 ring-indigo-400' : ''
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="rounded-xl bg-indigo-50 p-2 text-indigo-500">
                        {typeIconMap[environment.type] ?? (
                          <Server className="h-5 w-5" />
                        )}
                      </span>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-slate-900">
                            {environment.display_name}
                          </span>
                          {environment.policies?.risk_level && (
                            <span
                              className={`rounded-full px-2.5 py-0.5 text-[10px] font-medium ${riskBadge(
                                environment.policies.risk_level
                              )}`}
                            >
                              {environment.policies.risk_level.toUpperCase()}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500">
                          Тип: {environment.type}{' '}
                          {environment.metadata?.region
                            ? `• Регион: ${environment.metadata.region}`
                            : ''}
                        </p>
                        {environment.notes && (
                          <p className="text-xs text-slate-500">{environment.notes}</p>
                        )}
                        {environment.ssh?.host && (
                          <p className="text-xs text-slate-500">
                            SSH: {environment.ssh.username}@{environment.ssh.host}:
                            {environment.ssh.port ?? 22}
                          </p>
                        )}
                      </div>
                    </div>
                    {isSelected && (
                      <span className="rounded-full bg-indigo-100 p-2 text-indigo-600">
                        <Check className="h-4 w-4" />
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-slate-100 bg-slate-50 px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  )
}

