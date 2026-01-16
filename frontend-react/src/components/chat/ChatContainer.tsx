import { useRef, useEffect } from 'react';
import { MessageSquare } from 'lucide-react';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import type { Message } from '../../types';

interface ChatContainerProps {
  messages: Message[];
  isStreaming: boolean;
  error?: string | null;
  onSend: (message: string, selectedMessages?: Message[]) => void;
  onStop: () => void;
  agentColor?: string;
  greeting?: string;
  disabled?: boolean;
  selectedMessages?: Set<number>;
  selectionMode?: boolean;
  onToggleSelection?: (messageId: number) => void;
  draftMessage: string;
  onDraftChange: (value: string) => void;
}

export function ChatContainer({
  messages,
  isStreaming,
  error,
  onSend,
  onStop,
  agentColor,
  greeting,
  disabled,
  selectedMessages = new Set(),
  selectionMode = false,
  onToggleSelection,
  draftMessage,
  onDraftChange,
}: ChatContainerProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = (content: string) => {
    const selected = selectionMode
      ? messages.filter((m) => selectedMessages.has(m.id))
      : undefined;
    onSend(content, selected);
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
      {/* Messages area */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin"
      >
        {messages.length === 0 ? (
          // Empty state with greeting
          <div className="h-full flex flex-col items-center justify-center text-center px-4">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
              style={{ backgroundColor: agentColor ? `${agentColor}20` : '#4A90E220' }}
            >
              <MessageSquare
                size={32}
                style={{ color: agentColor || '#4A90E2' }}
              />
            </div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-2">
              开始新对话
            </h3>
            {greeting && (
              <p className="text-gray-500 dark:text-gray-400 max-w-md">
                {greeting}
              </p>
            )}
          </div>
        ) : (
          // Messages list
          <>
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                agentColor={agentColor}
                isSelected={selectedMessages.has(message.id)}
                onSelect={() => onToggleSelection?.(message.id)}
                selectionMode={selectionMode}
              />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800">
          <p className="text-red-600 dark:text-red-400 text-sm text-center">
            {error}
          </p>
        </div>
      )}

      {/* Streaming indicator */}
      {isStreaming && (
        <div className="px-4 py-2 bg-gray-50 dark:bg-gray-700/50">
          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 text-sm">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-current rounded-full animate-bounce" />
              <span
                className="w-2 h-2 bg-current rounded-full animate-bounce"
                style={{ animationDelay: '0.1s' }}
              />
              <span
                className="w-2 h-2 bg-current rounded-full animate-bounce"
                style={{ animationDelay: '0.2s' }}
              />
            </div>
            <span>正在思考...</span>
          </div>
        </div>
      )}

      {/* Input area */}
      <ChatInput
        onSend={handleSend}
        onStop={onStop}
        isStreaming={isStreaming}
        disabled={disabled}
        agentColor={agentColor}
        placeholder={disabled ? '请先选择或创建对话' : '输入消息...'}
        value={draftMessage}
        onChange={onDraftChange}
      />
    </div>
  );
}
