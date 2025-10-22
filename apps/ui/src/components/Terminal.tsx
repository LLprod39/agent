/**
 * Interactive Terminal Component
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { taskApi } from '@/lib/api';

interface TerminalLine {
  type: 'input' | 'output' | 'error' | 'system';
  content: string;
  timestamp: Date;
}

export const Terminal: React.FC = () => {
  const [lines, setLines] = useState<TerminalLine[]>([
    {
      type: 'system',
      content: 'DevOps LLM Agent Terminal - Type "help" for commands',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [isExecuting, setIsExecuting] = useState(false);
  const terminalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [lines]);

  const addLine = (type: TerminalLine['type'], content: string) => {
    setLines((prev) => [...prev, { type, content, timestamp: new Date() }]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isExecuting) return;

    const command = input.trim();
    addLine('input', `$ ${command}`);
    setInput('');

    // Add to history
    setHistory((prev) => [...prev, command]);
    setHistoryIndex(-1);

    // Handle special commands
    if (command.toLowerCase() === 'help') {
      showHelp();
      return;
    }

    if (command.toLowerCase() === 'clear') {
      setLines([]);
      return;
    }

    if (command.toLowerCase() === 'history') {
      history.forEach((cmd, i) => {
        addLine('output', `${i + 1}  ${cmd}`);
      });
      return;
    }

    // Execute as task
    setIsExecuting(true);
    try {
      addLine('system', 'Creating task...');
      const result = await taskApi.createTask({
        task: command,
        environment_profile: 'dev-vm',
        context: {},
        auto_approve: false,
      });

      addLine('output', `Task created: ${result.task_id || result.id}`);
      addLine('output', `Status: ${result.status}`);

      if (result.message) {
        addLine('output', result.message);
      }
    } catch (error: any) {
      addLine('error', `Error: ${error.message || 'Task execution failed'}`);
    } finally {
      setIsExecuting(false);
    }
  };

  const showHelp = () => {
    const helpText = [
      '',
      'Available Commands:',
      '  help      - Show this help',
      '  clear     - Clear terminal',
      '  history   - Show command history',
      '',
      'Examples:',
      '  Check server health for web-01',
      '  Find errors in nginx logs',
      '  Restart postgresql service',
      '',
    ];

    helpText.forEach((line) => addLine('output', line));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length === 0) return;

      const newIndex =
        historyIndex === -1 ? history.length - 1 : Math.max(0, historyIndex - 1);
      setHistoryIndex(newIndex);
      setInput(history[newIndex]);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex === -1) return;

      const newIndex = historyIndex + 1;
      if (newIndex >= history.length) {
        setHistoryIndex(-1);
        setInput('');
      } else {
        setHistoryIndex(newIndex);
        setInput(history[newIndex]);
      }
    }
  };

  const getLineColor = (type: TerminalLine['type']) => {
    switch (type) {
      case 'input':
        return 'text-green-400';
      case 'output':
        return 'text-gray-300';
      case 'error':
        return 'text-red-400';
      case 'system':
        return 'text-blue-400';
      default:
        return 'text-gray-300';
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
      {/* Terminal Output */}
      <div
        ref={terminalRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-sm"
        onClick={() => inputRef.current?.focus()}
      >
        {lines.map((line, i) => (
          <div key={i} className={`${getLineColor(line.type)} mb-1`}>
            {line.content}
          </div>
        ))}

        {/* Current Input Line */}
        {isExecuting && (
          <div className="text-yellow-400 animate-pulse">Executing...</div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t border-gray-700 p-4">
        <div className="flex items-center space-x-2 font-mono text-sm">
          <span className="text-green-400">$</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isExecuting}
            className="flex-1 bg-transparent text-white outline-none disabled:opacity-50"
            placeholder="Enter command..."
            autoFocus
          />
        </div>
      </form>
    </div>
  );
};

export default Terminal;
