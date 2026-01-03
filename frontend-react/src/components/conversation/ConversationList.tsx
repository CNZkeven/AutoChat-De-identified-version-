import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  MessageSquare,
  Trash2,
  Edit2,
  Check,
  X,
  Loader2,
} from 'lucide-react';
import type { Conversation } from '../../types';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface ConversationListProps {
  conversations: Conversation[];
  currentId: number | null;
  onSelect: (id: number) => void;
  onCreate: () => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  onRename: (id: number, title: string) => Promise<void>;
  loading?: boolean;
  agentColor?: string;
}

export function ConversationList({
  conversations,
  currentId,
  onSelect,
  onCreate,
  onDelete,
  onRename,
  loading,
  agentColor,
}: ConversationListProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    setCreating(true);
    try {
      await onCreate();
    } finally {
      setCreating(false);
    }
  };

  const handleStartEdit = (conv: Conversation) => {
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const handleSaveEdit = async () => {
    if (editingId && editTitle.trim()) {
      await onRename(editingId, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditTitle('');
  };

  const formatTime = (dateString: string) => {
    try {
      return formatDistanceToNow(new Date(dateString), {
        addSuffix: true,
        locale: zhCN,
      });
    } catch {
      return '';
    }
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={handleCreate}
          disabled={creating}
          className="w-full py-2.5 px-4 rounded-xl text-white font-medium transition-all hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2"
          style={{ backgroundColor: agentColor || '#4A90E2' }}
        >
          {creating ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <Plus size={18} />
          )}
          新建对话
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="animate-spin text-gray-400" size={24} />
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-8 px-4">
            <MessageSquare className="mx-auto mb-3 text-gray-300 dark:text-gray-600" size={40} />
            <p className="text-gray-500 dark:text-gray-400 text-sm">暂无对话</p>
            <p className="text-gray-400 dark:text-gray-500 text-xs mt-1">
              点击上方按钮开始新对话
            </p>
          </div>
        ) : (
          <AnimatePresence>
            {conversations.map((conv) => (
              <motion.div
                key={conv.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className={`group relative border-b border-gray-100 dark:border-gray-700 last:border-b-0 ${
                  conv.id === currentId
                    ? 'bg-gray-50 dark:bg-gray-700/50'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700/30'
                }`}
              >
                {editingId === conv.id ? (
                  // Edit mode
                  <div className="p-3 flex items-center gap-2">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="flex-1 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveEdit();
                        if (e.key === 'Escape') handleCancelEdit();
                      }}
                    />
                    <button
                      onClick={handleSaveEdit}
                      className="p-1 text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
                    >
                      <Check size={16} />
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  // Normal mode
                  <button
                    onClick={() => onSelect(conv.id)}
                    className="w-full text-left p-3 pr-20"
                  >
                    <div className="flex items-start gap-3">
                      <MessageSquare
                        size={18}
                        className="flex-shrink-0 mt-0.5"
                        style={{
                          color: conv.id === currentId ? agentColor : undefined,
                        }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-800 dark:text-gray-200 truncate text-sm">
                          {conv.title}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          {formatTime(conv.updated_at)}
                        </p>
                      </div>
                    </div>

                    {/* Active indicator */}
                    {conv.id === currentId && (
                      <div
                        className="absolute left-0 top-0 bottom-0 w-1 rounded-r"
                        style={{ backgroundColor: agentColor }}
                      />
                    )}
                  </button>
                )}

                {/* Action buttons (visible on hover) */}
                {editingId !== conv.id && (
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStartEdit(conv);
                      }}
                      className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm('确定要删除这个对话吗？')) {
                          onDelete(conv.id);
                        }
                      }}
                      className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
