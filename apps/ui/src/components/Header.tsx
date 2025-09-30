'use client'

import { useState } from 'react'
import { Menu, Settings, Bell, User } from 'lucide-react'
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
    <header className="bg-white border-b border-gray-200 px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Left side */}
        <div className="flex items-center space-x-4">
          <button
            onClick={onMenuClick}
            className="p-2 rounded-md hover:bg-gray-100 lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>
          
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-semibold text-gray-900">
              DevOps LLM Agent
            </h1>
            <span className="text-sm text-gray-500">v0.1.0</span>
          </div>
        </div>

        {/* Center - Environment Selector */}
        <div className="flex-1 max-w-md mx-4">
          <button
            onClick={() => setShowEnvironmentSelector(true)}
            className="w-full px-3 py-2 text-left bg-gray-50 border border-gray-300 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {selectedEnvironment ? (
              <div>
                <div className="font-medium text-gray-900">
                  {selectedEnvironment.display_name}
                </div>
                <div className="text-sm text-gray-500">
                  {selectedEnvironment.type} • {selectedEnvironment.metadata?.region || 'Unknown'}
                </div>
              </div>
            ) : (
              <div className="text-gray-500">Select Environment</div>
            )}
          </button>
        </div>

        {/* Right side */}
        <div className="flex items-center space-x-2">
          <button className="p-2 rounded-md hover:bg-gray-100">
            <Bell className="h-5 w-5 text-gray-600" />
          </button>
          
          <button className="p-2 rounded-md hover:bg-gray-100">
            <Settings className="h-5 w-5 text-gray-600" />
          </button>
          
          <button className="p-2 rounded-md hover:bg-gray-100">
            <User className="h-5 w-5 text-gray-600" />
          </button>
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




