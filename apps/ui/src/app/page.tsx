'use client'

import { useState, useEffect } from 'react'
import { ChatInterface } from '@/components/ChatInterface'
import { EnvironmentSelector } from '@/components/EnvironmentSelector'
import { TaskMonitor } from '@/components/TaskMonitor'
import { Header } from '@/components/Header'
import { Sidebar } from '@/components/Sidebar'
import { Environment } from '@/types/environment'

export default function Home() {
  const [selectedEnvironment, setSelectedEnvironment] = useState<Environment | null>(null)
  const [activeTasks, setActiveTasks] = useState<any[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    // Load environments and tasks on mount
    loadEnvironments()
    loadActiveTasks()
  }, [])

  const loadEnvironments = async () => {
    try {
      const response = await fetch('/api/v1/environments')
      const data = await response.json()
      if (data.environments && data.environments.length > 0) {
        setSelectedEnvironment(data.environments[0])
      }
    } catch (error) {
      console.error('Failed to load environments:', error)
    }
  }

  const loadActiveTasks = async () => {
    try {
      const response = await fetch('/api/v1/tasks')
      const data = await response.json()
      setActiveTasks(data.tasks || [])
    } catch (error) {
      console.error('Failed to load active tasks:', error)
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)}
        activeTasks={activeTasks}
        onTaskUpdate={loadActiveTasks}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <Header 
          onMenuClick={() => setSidebarOpen(true)}
          selectedEnvironment={selectedEnvironment}
          onEnvironmentChange={setSelectedEnvironment}
        />

        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Chat Interface */}
          <div className="flex-1 flex flex-col">
            <ChatInterface 
              selectedEnvironment={selectedEnvironment}
              onTaskCreated={loadActiveTasks}
            />
          </div>

          {/* Task Monitor */}
          <div className="w-80 border-l border-gray-200 bg-white">
            <TaskMonitor 
              tasks={activeTasks}
              onTaskUpdate={loadActiveTasks}
            />
          </div>
        </div>
      </div>
    </div>
  )
}




