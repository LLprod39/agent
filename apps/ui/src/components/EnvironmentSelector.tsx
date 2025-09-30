'use client'

import { useState, useEffect } from 'react'
import { X, Check, AlertCircle } from 'lucide-react'
import { Environment } from '@/types/environment'
import { environmentApi } from '@/lib/api'

interface EnvironmentSelectorProps {
  selectedEnvironment: Environment | null
  onEnvironmentChange: (environment: Environment) => void
  onClose: () => void
}

export function EnvironmentSelector({ 
  selectedEnvironment, 
  onEnvironmentChange, 
  onClose 
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
    } catch (err) {
      setError('Failed to load environments')
      console.error('Error loading environments:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleEnvironmentSelect = (environment: Environment) => {
    onEnvironmentChange(environment)
    onClose()
  }

  const getRiskColor = (riskLevel?: string) => {
    switch (riskLevel) {
      case 'high':
        return 'text-red-600'
      case 'medium':
        return 'text-yellow-600'
      case 'low':
        return 'text-green-600'
      default:
        return 'text-gray-600'
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'k8s':
        return '☸️'
      case 'vm':
        return '🖥️'
      case 'docker':
        return '🐳'
      case 'bare_metal':
        return '🖲️'
      default:
        return '🔧'
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />
      
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Select Environment</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-md hover:bg-gray-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="mt-2 text-gray-600">Loading environments...</p>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <p className="text-red-600">{error}</p>
              <button
                onClick={loadEnvironments}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                Retry
              </button>
            </div>
          ) : environments.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-600">No environments available</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {environments.map((environment) => (
                <div
                  key={environment.id}
                  className={`p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
                    selectedEnvironment?.id === environment.id ? 'ring-2 ring-blue-500 bg-blue-50' : ''
                  }`}
                  onClick={() => handleEnvironmentSelect(environment)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{getTypeIcon(environment.type)}</span>
                      <div>
                        <h3 className="font-medium text-gray-900">
                          {environment.display_name}
                        </h3>
                        <p className="text-sm text-gray-600">
                          {environment.type} • {environment.metadata?.region || 'Unknown'}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      {environment.policies?.risk_level && (
                        <span className={`text-sm font-medium ${getRiskColor(environment.policies.risk_level)}`}>
                          {environment.policies.risk_level.toUpperCase()}
                        </span>
                      )}
                      
                      {selectedEnvironment?.id === environment.id && (
                        <Check className="h-5 w-5 text-blue-500" />
                      )}
                    </div>
                  </div>
                  
                  {environment.notes && (
                    <p className="mt-2 text-sm text-gray-600">
                      {environment.notes}
                    </p>
                  )}
                  
                  {environment.policies?.require_approval && (
                    <div className="mt-2">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        Requires Approval
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end space-x-3 p-6 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}





