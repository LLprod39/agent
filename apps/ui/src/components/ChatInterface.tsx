'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, AlertCircle, CheckCircle, Clock } from 'lucide-react'
import { Environment } from '@/types/environment'
import { Message } from '@/types/chat'
import { chatApi } from '@/lib/api'
import { ChatMessage } from './ChatMessage'

interface ChatInterfaceProps {
  selectedEnvironment: Environment | null
  onTaskCreated: () => void
}

export function ChatInterface({ selectedEnvironment, onTaskCreated }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await chatApi.sendMessage({
        message: userMessage.content,
        session_id: sessionId || undefined,
        environment_profile: selectedEnvironment?.id,
        context: {
          environment: selectedEnvironment,
        },
      })

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.message,
        timestamp: new Date().toISOString(),
        metadata: {
          task_id: response.task_id,
          requires_approval: response.requires_approval,
          risk_level: response.risk_level,
        },
      }

      setMessages(prev => [...prev, assistantMessage])
      
      if (response.task_id) {
        setSessionId(response.task_id)
        onTaskCreated()
      }

    } catch (error) {
      console.error('Error sending message:', error)
      
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your request. Please try again.',
        timestamp: new Date().toISOString(),
        metadata: {
          error: true,
        },
      }

      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
    setSessionId(null)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="flex items-center justify-between p-4 border-b bg-white">
        <div>
          <h2 className="text-lg font-semibold">DevOps Assistant</h2>
          {selectedEnvironment && (
            <p className="text-sm text-gray-600">
              Environment: {selectedEnvironment.display_name}
            </p>
          )}
        </div>
        <button
          onClick={clearChat}
          className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded"
        >
          Clear Chat
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🤖</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Welcome to DevOps LLM Agent
            </h3>
            <p className="text-gray-600 mb-6">
              I can help you with DevOps tasks like deploying applications, managing infrastructure, and troubleshooting issues.
            </p>
            <div className="text-left max-w-md mx-auto">
              <p className="text-sm text-gray-500 mb-2">Try asking me to:</p>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Deploy nginx to the cluster</li>
                <li>• Check the status of all pods</li>
                <li>• Scale a deployment to 3 replicas</li>
                <li>• Show me the logs for a specific pod</li>
              </ul>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))
        )}
        
        {isLoading && (
          <div className="flex items-center space-x-2 text-gray-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Thinking...</span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t bg-white">
        <div className="flex space-x-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me to help with DevOps tasks..."
            className="flex-1 p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={2}
            disabled={isLoading}
          />
          <button
            onClick={handleSendMessage}
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
        
        {selectedEnvironment && (
          <div className="mt-2 text-xs text-gray-500">
            Commands will be executed in: {selectedEnvironment.display_name} ({selectedEnvironment.type})
          </div>
        )}
      </div>
    </div>
  )
}





