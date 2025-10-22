'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Sparkles, ArrowRight } from 'lucide-react'
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

    setMessages((prev) => [...prev, userMessage])
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

      setMessages((prev) => [...prev, assistantMessage])

      if (response.task_id) {
        setSessionId(response.task_id)
        onTaskCreated()
      }
    } catch (error) {
      console.error('Error sending message:', error)

      const errorMessage: Message = {
        role: 'assistant',
        content:
          'Произошла ошибка при обработке запроса. Попробуйте еще раз или проверьте логи сервиса.',
        timestamp: new Date().toISOString(),
        metadata: {
          error: true,
        },
      }

      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
    setSessionId(null)
  }

  return (
    <div className="flex h-full flex-col">
      {/* Chat Header */}
      <div className="flex items-center justify-between border-b border-indigo-100 bg-gradient-to-r from-indigo-500 via-blue-500 to-sky-500 px-5 py-4 text-white shadow-sm">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">DevOps Assistant</h2>
          {selectedEnvironment ? (
            <p className="text-xs text-indigo-100">
              Окружение: {selectedEnvironment.display_name} ({selectedEnvironment.type})
            </p>
          ) : (
            <p className="text-xs text-indigo-100">
              Выберите окружение, чтобы выполнять команды.
            </p>
          )}
        </div>
        <button
          onClick={clearChat}
          className="rounded-full border border-white/40 px-3 py-1 text-xs font-medium text-white/90 transition hover:bg-white/10"
        >
          Очистить историю
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-4 overflow-y-auto bg-slate-50 px-5 py-5">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center rounded-3xl border border-dashed border-indigo-200 bg-white/70 px-6 py-10 text-center shadow-inner">
            <div className="mb-4 rounded-2xl bg-indigo-50 p-4 text-indigo-500">
              <Sparkles className="h-10 w-10" />
            </div>
            <h3 className="mb-2 text-xl font-semibold text-gray-900">Добро пожаловать!</h3>
            <p className="mb-6 max-w-lg text-sm text-gray-600">
              Я готов помочь с деплоем, диагностикой и автоматизацией. Ниже несколько
              примеров запросов, которые можно задать.
            </p>
            <div className="mx-auto w-full max-w-md rounded-2xl border border-indigo-100 bg-indigo-50/60 p-4 text-left">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-indigo-600">
                Попробуйте запросы
              </p>
              <ul className="space-y-2 text-sm text-indigo-900">
                <li className="flex items-start gap-2 rounded-lg bg-white/80 px-3 py-2 shadow-sm">
                  <ArrowRight className="mt-0.5 h-4 w-4 text-indigo-500" />
                  <span>Разверни nginx в namespace staging и пришли URL сервиса</span>
                </li>
                <li className="flex items-start gap-2 rounded-lg bg-white/80 px-3 py-2 shadow-sm">
                  <ArrowRight className="mt-0.5 h-4 w-4 text-indigo-500" />
                  <span>Разбери 500 ошибки сервиса checkout и предложи план фикса</span>
                </li>
                <li className="flex items-start gap-2 rounded-lg bg-white/80 px-3 py-2 shadow-sm">
                  <ArrowRight className="mt-0.5 h-4 w-4 text-indigo-500" />
                  <span>Собери метрики CPU и использования памяти на bastion</span>
                </li>
              </ul>
            </div>
          </div>
        ) : (
          messages.map((message, index) => <ChatMessage key={index} message={message} />)
        )}

        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Думаю над ответом…</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-100 bg-white px-5 py-4">
        <div className="flex space-x-2">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Например: «Проверь логи сервиса checkout за последние 5 минут»"
            className="flex-1 resize-none rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm shadow-inner focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            rows={2}
            disabled={isLoading}
          />
          <button
            onClick={handleSendMessage}
            disabled={!input.trim() || isLoading}
            className="inline-flex items-center gap-2 rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Отправить
          </button>
        </div>

        {selectedEnvironment && (
          <div className="mt-2 text-xs text-gray-500">
            Команды выполняются в окружении: {selectedEnvironment.display_name} (
            {selectedEnvironment.type})
          </div>
        )}
      </div>
    </div>
  )
}
