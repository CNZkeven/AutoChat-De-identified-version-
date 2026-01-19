import { memo } from 'react';
import { User, Bot, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import type { Message } from '../../types';

interface MessageBubbleProps {
  message: Message;
  agentColor?: string;
  isSelected?: boolean;
  onSelect?: () => void;
  selectionMode?: boolean;
}

export const MessageBubble = memo(function MessageBubble({
  message,
  agentColor,
  isSelected,
  onSelect,
  selectionMode,
}: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} animate-fade-in`}
      onClick={selectionMode ? onSelect : undefined}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center ${
          isUser
            ? 'bg-gray-200 dark:bg-gray-700'
            : 'text-white'
        }`}
        style={!isUser && agentColor ? { backgroundColor: agentColor } : undefined}
      >
        {isUser ? (
          <User size={18} className="text-gray-600 dark:text-gray-300" />
        ) : (
          <Bot size={18} />
        )}
      </div>

      {/* Message content */}
      <div
        className={`relative max-w-[80%] ${
          selectionMode ? 'cursor-pointer' : ''
        }`}
      >
        {/* Selection indicator */}
        {selectionMode && (
          <div
            className={`absolute -left-7 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
              isSelected
                ? 'bg-primary-500 border-primary-500'
                : 'border-gray-300 dark:border-gray-600'
            }`}
          >
            {isSelected && <Check size={12} className="text-white" />}
          </div>
        )}

        {/* Bubble */}
        <div
          className={`px-4 py-3 rounded-2xl ${
            isUser
              ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-br-md'
              : 'text-white rounded-bl-md'
          } ${selectionMode && isSelected ? 'ring-2 ring-primary-500' : ''}`}
          style={!isUser && agentColor ? { backgroundColor: agentColor } : undefined}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          ) : (
            <div className="markdown-body prose prose-sm prose-invert max-w-none prose-p:my-1 prose-headings:my-2">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                  table: ({ children }) => (
                    <div className="my-3 overflow-x-auto">
                      <table className="w-full border-collapse text-sm">{children}</table>
                    </div>
                  ),
                  thead: ({ children }) => <thead className="bg-white/10">{children}</thead>,
                  th: ({ children }) => (
                    <th className="px-3 py-2 text-left font-semibold border-b border-white/20">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-3 py-2 align-top border-b border-white/10">{children}</td>
                  ),
                  code: ({ inline, className, children }) => {
                    if (inline) {
                      return (
                        <code className="px-1 py-0.5 rounded bg-white/10 text-[0.85em]">
                          {children}
                        </code>
                      );
                    }
                    return (
                      <pre className="my-2 overflow-x-auto rounded-lg bg-black/60 p-3 text-xs text-white">
                        <code className={className}>{children}</code>
                      </pre>
                    );
                  },
                }}
              >
                {message.content || '...'}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div
          className={`text-xs text-gray-400 mt-1 ${isUser ? 'text-right' : 'text-left'}`}
        >
          {new Date(message.created_at).toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
    </div>
  );
});
