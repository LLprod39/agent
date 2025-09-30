'use client'

import { useState } from 'react'
import { Copy, Check, AlertCircle, Clock, CheckCircle, XCircle } from 'lucide-react'
import { Message } from '@/types/chat'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [copied, setCopied] = useState(false)

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy text: ', err)
    }
  }

  const getStatusIcon = () => {
    if (message.metadata?.error) {
      return <XCircle className="h-4 w-4 text-red-500" />
    }
    
    if (message.metadata?.requires_approval) {
      return <AlertCircle className="h-4 w-4 text-yellow-500" />
    }
    
    if (message.metadata?.task_id) {
      return <CheckCircle className="h-4 w-4 text-green-500" />
    }
    
    return null
  }

  const getRiskBadge = () => {
    if (!message.metadata?.risk_level) return null
    
    const riskLevel = message.metadata.risk_level
    const colors = {
      low: 'bg-green-100 text-green-800',
      medium: 'bg-yellow-100 text-yellow-800',
      high: 'bg-red-100 text-red-800',
    }
    
    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${colors[riskLevel as keyof typeof colors]}`}>
        {riskLevel.toUpperCase()} RISK
      </span>
    )
  }

  return (
    <div className={`chat-message ${message.role}`}>
      <div className="flex items-start space-x-3">
        {/* Avatar */}
        <div className="flex-shrink-0">
          {message.role === 'user' ? (
            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
              U
            </div>
          ) : (
            <div className="w-8 h-8 bg-gray-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
              🤖
            </div>
          )}
        </div>

        {/* Message Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-sm font-medium text-gray-900">
              {message.role === 'user' ? 'You' : 'DevOps Agent'}
            </span>
            <span className="text-xs text-gray-500">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
            {getStatusIcon()}
            {getRiskBadge()}
          </div>

          <div className="prose prose-sm max-w-none">
            <ReactMarkdown
              components={{
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '')
                  return !inline && match ? (
                    <SyntaxHighlighter
                      style={tomorrow}
                      language={match[1]}
                      PreTag="div"
                      className="rounded-md"
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className="bg-gray-100 px-1 py-0.5 rounded text-sm" {...props}>
                      {children}
                    </code>
                  )
                },
                pre({ children }) {
                  return <div className="not-prose">{children}</div>
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>

          {/* Task ID */}
          {message.metadata?.task_id && (
            <div className="mt-2 text-xs text-gray-500">
              Task ID: {message.metadata.task_id}
            </div>
          )}

          {/* Approval Required */}
          {message.metadata?.requires_approval && (
            <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 text-yellow-600" />
                <span className="text-sm font-medium text-yellow-800">
                  Approval Required
                </span>
              </div>
              <p className="text-sm text-yellow-700 mt-1">
                This task requires manual approval before execution due to high risk.
              </p>
            </div>
          )}
        </div>

        {/* Copy Button */}
        <button
          onClick={copyToClipboard}
          className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600"
          title="Copy message"
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-500" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  )
}





