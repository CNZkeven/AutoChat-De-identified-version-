import { useState, useRef, useEffect } from 'react';
import { Send, Square, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  placeholder?: string;
  agentColor?: string;
}

export function ChatInput({
  onSend,
  onStop,
  isStreaming,
  disabled,
  placeholder = '输入消息...',
  agentColor,
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  }, [message]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (message.trim() && !isStreaming && !disabled) {
      onSend(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      <form onSubmit={handleSubmit} className="flex gap-3 items-end">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isStreaming}
            rows={1}
            className="w-full px-4 py-3 bg-gray-100 dark:bg-gray-700 border-0 rounded-xl text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none transition-all scrollbar-thin"
            style={{
              minHeight: '48px',
              maxHeight: '200px',
            }}
          />
        </div>

        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            className="flex-shrink-0 p-3 rounded-xl bg-red-500 hover:bg-red-600 text-white transition-colors"
            aria-label="Stop generation"
          >
            <Square size={20} fill="currentColor" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!message.trim() || disabled}
            className="flex-shrink-0 p-3 rounded-xl text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90"
            style={{
              backgroundColor: agentColor || '#4A90E2',
            }}
            aria-label="Send message"
          >
            {disabled ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <Send size={20} />
            )}
          </button>
        )}
      </form>

      {/* Helper text */}
      <p className="text-xs text-gray-400 mt-2 text-center">
        按 Enter 发送，Shift + Enter 换行
      </p>
    </div>
  );
}
