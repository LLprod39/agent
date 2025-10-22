'use client'

import { useMemo, useState } from 'react'
import {
  Plus,
  Server,
  ShieldAlert,
  ShieldCheck,
  ShieldHalf,
  Trash2,
  X,
  Loader2,
  Copy,
  Check,
} from 'lucide-react'
import { environmentApi } from '@/lib/api'
import {
  Environment,
  CreateEnvironmentRequest,
  SSHConfig,
  SSHJumpHost,
} from '@/types/environment'

type RiskLevel = 'low' | 'medium' | 'high'

interface MachineManagerProps {
  environments: Environment[]
  onRefresh: () => Promise<void> | void
  onSelectEnvironment?: (environment: Environment) => void
}

interface MachineFormState {
  displayName: string
  description: string
  host: string
  port: number
  username: string
  authMethod: 'password' | 'key'
  password: string
  privateKey: string
  passphrase: string
  riskLevel: RiskLevel
  notes: string
  becomeUser: string
  sudoPassword: string
  jumpHostEnabled: boolean
  jumpHostHost: string
  jumpHostPort: number
  jumpHostUsername: string
  jumpHostPassword: string
  jumpHostKey: string
}

const initialFormState: MachineFormState = {
  displayName: '',
  description: '',
  host: '',
  port: 22,
  username: '',
  authMethod: 'password',
  password: '',
  privateKey: '',
  passphrase: '',
  riskLevel: 'low',
  notes: '',
  becomeUser: '',
  sudoPassword: '',
  jumpHostEnabled: false,
  jumpHostHost: '',
  jumpHostPort: 22,
  jumpHostUsername: '',
  jumpHostPassword: '',
  jumpHostKey: '',
}

const riskLevelIcon = (risk: RiskLevel) => {
  switch (risk) {
    case 'low':
      return <ShieldCheck className="h-5 w-5 text-emerald-500" />
    case 'medium':
      return <ShieldHalf className="h-5 w-5 text-amber-500" />
    case 'high':
      return <ShieldAlert className="h-5 w-5 text-rose-500" />
    default:
      return null
  }
}

const riskLevelBadge = (risk: RiskLevel) => {
  switch (risk) {
    case 'low':
      return 'bg-emerald-100 text-emerald-700'
    case 'medium':
      return 'bg-amber-100 text-amber-700'
    case 'high':
      return 'bg-rose-100 text-rose-700'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}

const slugify = (value: string) =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')

const buildSSHConfig = (form: MachineFormState): SSHConfig => {
  const jumpHost: SSHJumpHost | undefined = form.jumpHostEnabled
    ? {
        host: form.jumpHostHost.trim(),
        port: form.jumpHostPort || 22,
        username: form.jumpHostUsername.trim(),
        password: form.jumpHostPassword.trim() || undefined,
        private_key: form.jumpHostKey.trim() || undefined,
      }
    : undefined

  const sshConfig: SSHConfig = {
    host: form.host.trim(),
    port: form.port || 22,
    username: form.username.trim(),
    passphrase: form.passphrase.trim() || undefined,
    sudo_password: form.sudoPassword.trim() || undefined,
    become_user: form.becomeUser.trim() || undefined,
    jump_host: jumpHost,
    max_connection_attempts: 3,
  }

  if (form.authMethod === 'password' && form.password.trim()) {
    sshConfig.password = form.password.trim()
  }

  if (form.authMethod === 'key' && form.privateKey.trim()) {
    sshConfig.private_key = form.privateKey.trim()
  }

  return sshConfig
}

export function MachineManager({
  environments,
  onRefresh,
  onSelectEnvironment,
}: MachineManagerProps) {
  const [isCreating, setIsCreating] = useState(false)
  const [formState, setFormState] = useState<MachineFormState>(initialFormState)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Environment | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const machines = useMemo(
    () =>
      environments.filter(
        (env) =>
          Boolean(env.ssh) ||
          env.metadata?.category === 'ssh-machine' ||
          env.type === 'vm'
      ),
    [environments]
  )

  const handleInputChange = <K extends keyof MachineFormState>(
    key: K,
    value: MachineFormState[K]
  ) => {
    setFormState((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  const resetForm = () => {
    setFormState(initialFormState)
  }

  const handleCreateMachine = async () => {
    if (!formState.displayName.trim() || !formState.host.trim() || !formState.username.trim()) {
      return
    }

    const environmentId = slugify(formState.displayName || formState.host)
    if (!environmentId) {
      return
    }

    const sshConfig = buildSSHConfig(formState)

    const payload: CreateEnvironmentRequest = {
      id: environmentId,
      type: 'vm',
      display_name: formState.displayName.trim(),
      description: formState.description.trim() || undefined,
      networking: {
        proxy: {},
      },
      auth: {},
      policies: {
        risk_level: formState.riskLevel,
        require_approval: formState.riskLevel !== 'low',
      },
      defaults: {
        working_directory: '/tmp',
        retries: 0,
      },
      metadata: {
        category: 'ssh-machine',
        created_from: 'ui',
      },
      notes: formState.notes.trim() || undefined,
      ssh: sshConfig,
      extensions: { ssh: sshConfig },
    }

    try {
      setError(null)
      setSuccess(null)
      setIsSubmitting(true)
      await environmentApi.createEnvironment(payload)
      await Promise.resolve(onRefresh())
      setIsCreating(false)
      resetForm()
      setSuccess('Сервер успешно добавлен.')
      setTimeout(() => setSuccess(null), 4000)
    } catch (err: any) {
      console.error('Failed to create machine', err)
      const message =
        err?.response?.data?.detail?.message ??
        err?.response?.data?.detail ??
        err?.message ??
        'Не удалось создать профиль окружения.'
      setError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeleteMachine = async (environmentId: string) => {
    try {
      setIsSubmitting(true)
      await environmentApi.deleteEnvironment(environmentId)
      await Promise.resolve(onRefresh())
      setDeleteTarget(null)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id).then(() => {
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    })
  }

  return (
    <div className="h-full flex flex-col">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">SSH Servers</h2>
          <p className="text-sm text-gray-600">
            Manage remote machines available to the DevOps agent. Add hosts, control access,
            and keep credentials up to date.
          </p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        >
          <Plus className="h-4 w-4" />
          Add machine
        </button>
      </div>

      {(error || success) && (
        <div className="mb-6 space-y-2">
          {error && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
              {error}
            </div>
          )}
          {success && (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {success}
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {machines.map((machine) => (
          <div
            key={machine.id}
            className="group relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition hover:border-indigo-200 hover:shadow-md"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                  <Server className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {machine.display_name || machine.id}
                    </h3>
                    {machine.policies?.risk_level && (
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${riskLevelBadge(
                          (machine.policies.risk_level as RiskLevel) || 'low'
                        )}`}
                      >
                        {riskLevelIcon(
                          (machine.policies?.risk_level as RiskLevel) || 'low'
                        )}
                        {machine.policies?.risk_level.toUpperCase()}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600">
                    {machine.ssh?.username}@{machine.ssh?.host}:{machine.ssh?.port ?? 22}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 opacity-0 transition group-hover:opacity-100">
                <button
                  className="rounded-lg border border-gray-200 p-2 text-gray-500 hover:border-gray-300 hover:text-gray-700"
                  onClick={() => handleCopyId(machine.id)}
                  title="Copy environment ID"
                >
                  {copiedId === machine.id ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </button>
                <button
                  className="rounded-lg border border-red-200 p-2 text-red-500 hover:border-red-300 hover:text-red-600"
                  onClick={() => setDeleteTarget(machine)}
                  title="Delete machine"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="mt-4 space-y-2 text-sm text-gray-600">
              {machine.notes && <p className="text-gray-600">{machine.notes}</p>}
              {machine.ssh?.jump_host && (
                <p>
                  <span className="font-medium text-gray-700">Jump host:</span>{' '}
                  {machine.ssh.jump_host.username}@{machine.ssh.jump_host.host}:
                  {machine.ssh.jump_host.port ?? 22}
                </p>
              )}
              {machine.metadata?.owner && (
                <p>
                  <span className="font-medium text-gray-700">Owner:</span>{' '}
                  {machine.metadata.owner}
                </p>
              )}
            </div>

            <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
              <span>Environment ID: {machine.id}</span>
              <button
                onClick={() => onSelectEnvironment?.(machine)}
                className="text-indigo-600 hover:text-indigo-500"
              >
                Use in chat →
              </button>
            </div>
          </div>
        ))}
      </div>

      {machines.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center">
          <Server className="mb-4 h-10 w-10 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900">No SSH machines yet</h3>
          <p className="mt-2 max-w-md text-sm text-gray-600">
            Add your first server to let the DevOps agent execute commands over SSH.
            Provide credentials or keys, and the agent will reuse them securely.
          </p>
          <button
            onClick={() => setIsCreating(true)}
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500"
          >
            <Plus className="h-4 w-4" />
            Add machine
          </button>
        </div>
      )}

      {/* Create machine modal */}
      {isCreating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-sm">
          <div className="relative w-full max-w-3xl rounded-3xl bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Add SSH machine
                </h3>
                <p className="text-sm text-gray-600">
                  Provide connection details for the host you want the agent to manage.
                </p>
              </div>
              <button
                onClick={() => {
                  setIsCreating(false)
                  resetForm()
                }}
                className="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="max-h-[70vh] space-y-6 overflow-y-auto px-6 py-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Display name
                  </label>
                  <input
                    type="text"
                    value={formState.displayName}
                    onChange={(event) =>
                      handleInputChange('displayName', event.target.value)
                    }
                    placeholder="e.g. staging-api-01"
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">Hostname</label>
                  <input
                    type="text"
                    value={formState.host}
                    onChange={(event) => handleInputChange('host', event.target.value)}
                    placeholder="host.example.com"
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">Port</label>
                  <input
                    type="number"
                    min={1}
                    max={65535}
                    value={formState.port}
                    onChange={(event) =>
                      handleInputChange('port', Number(event.target.value) || 22)
                    }
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">Username</label>
                  <input
                    type="text"
                    value={formState.username}
                    onChange={(event) =>
                      handleInputChange('username', event.target.value)
                    }
                    placeholder="e.g. ubuntu"
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Authentication
                  </label>
                  <select
                    value={formState.authMethod}
                    onChange={(event) =>
                      handleInputChange(
                        'authMethod',
                        event.target.value as MachineFormState['authMethod']
                      )
                    }
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  >
                    <option value="password">Password</option>
                    <option value="key">SSH key</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">Risk level</label>
                  <select
                    value={formState.riskLevel}
                    onChange={(event) =>
                      handleInputChange(
                        'riskLevel',
                        event.target.value as MachineFormState['riskLevel']
                      )
                    }
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>

              {formState.authMethod === 'password' ? (
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Password <span className="text-gray-400">(stored encrypted)</span>
                  </label>
                  <input
                    type="password"
                    value={formState.password}
                    onChange={(event) =>
                      handleInputChange('password', event.target.value)
                    }
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Private key (PEM)
                  </label>
                  <textarea
                    value={formState.privateKey}
                    onChange={(event) =>
                      handleInputChange('privateKey', event.target.value)
                    }
                    rows={6}
                    placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
              )}

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Key passphrase (optional)
                  </label>
                  <input
                    type="password"
                    value={formState.passphrase}
                    onChange={(event) =>
                      handleInputChange('passphrase', event.target.value)
                    }
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Become user (sudo -u)
                  </label>
                  <input
                    type="text"
                    value={formState.becomeUser}
                    onChange={(event) =>
                      handleInputChange('becomeUser', event.target.value)
                    }
                    placeholder="root"
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Sudo password (optional)
                  </label>
                  <input
                    type="password"
                    value={formState.sudoPassword}
                    onChange={(event) =>
                      handleInputChange('sudoPassword', event.target.value)
                    }
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Description (optional)
                  </label>
                  <input
                    type="text"
                    value={formState.description}
                    onChange={(event) =>
                      handleInputChange('description', event.target.value)
                    }
                    placeholder="Short summary of what this server does"
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                  />
                </div>
              </div>

              <div className="rounded-2xl border border-gray-200 bg-gray-50/60 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900">
                      Jump host (optional)
                    </h4>
                    <p className="text-xs text-gray-600">
                      Add a bastion host the agent should tunnel through.
                    </p>
                  </div>
                  <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                    <span>Enable</span>
                    <input
                      type="checkbox"
                      checked={formState.jumpHostEnabled}
                      onChange={(event) =>
                        handleInputChange('jumpHostEnabled', event.target.checked)
                      }
                      className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                  </label>
                </div>

                {formState.jumpHostEnabled && (
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">
                        Jump host
                      </label>
                      <input
                        type="text"
                        value={formState.jumpHostHost}
                        onChange={(event) =>
                          handleInputChange('jumpHostHost', event.target.value)
                        }
                        className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">Port</label>
                      <input
                        type="number"
                        value={formState.jumpHostPort}
                        min={1}
                        max={65535}
                        onChange={(event) =>
                          handleInputChange(
                            'jumpHostPort',
                            Number(event.target.value) || 22
                          )
                        }
                        className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">
                        Username
                      </label>
                      <input
                        type="text"
                        value={formState.jumpHostUsername}
                        onChange={(event) =>
                          handleInputChange('jumpHostUsername', event.target.value)
                        }
                        className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">
                        Password (optional)
                      </label>
                      <input
                        type="password"
                        value={formState.jumpHostPassword}
                        onChange={(event) =>
                          handleInputChange('jumpHostPassword', event.target.value)
                        }
                        className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                      />
                    </div>
                    <div className="md:col-span-2 space-y-2">
                      <label className="text-sm font-medium text-gray-700">
                        Private key (optional)
                      </label>
                      <textarea
                        value={formState.jumpHostKey}
                        onChange={(event) =>
                          handleInputChange('jumpHostKey', event.target.value)
                        }
                        rows={4}
                        className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">Notes</label>
                <textarea
                  value={formState.notes}
                  onChange={(event) => handleInputChange('notes', event.target.value)}
                  rows={3}
                  placeholder="Optional operational context or runbook references."
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-gray-100 px-6 py-4">
              <button
                onClick={() => {
                  setIsCreating(false)
                  resetForm()
                }}
                className="rounded-xl border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                onClick={handleCreateMachine}
                disabled={
                  isSubmitting ||
                  !formState.displayName.trim() ||
                  !formState.host.trim() ||
                  !formState.username.trim()
                }
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4" />
                    Create machine
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900">Delete machine</h3>
            <p className="mt-2 text-sm text-gray-600">
              Are you sure you want to delete{' '}
              <span className="font-medium text-gray-900">
                {deleteTarget.display_name || deleteTarget.id}
              </span>
              ? The agent will lose access to this host.
            </p>
            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="rounded-xl border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteMachine(deleteTarget.id)}
                className="inline-flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
