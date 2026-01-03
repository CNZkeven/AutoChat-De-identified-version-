import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { ChatContainer } from '../components/chat/ChatContainer';
import { ConversationList } from '../components/conversation/ConversationList';
import { useChat } from '../hooks/useChat';
import { conversationService } from '../services/conversations';
import { getAgentConfig } from '../utils/constants';
import { memoryService } from '../services/memory';
import { exportService } from '../services/export';
import {
  Brain,
  Download,
  Share2,
  CheckSquare,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import type { Conversation, AgentType } from '../types';

export function ChatPage() {
  const { agent } = useParams<{ agent: string }>();
  const navigate = useNavigate();

  // Validate agent type
  const agentConfig = agent ? getAgentConfig(agent) : undefined;
  const agentType = agentConfig?.type;

  // State
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedMessages, setSelectedMessages] = useState<Set<number>>(new Set());

  // Memory state
  const [memory, setMemory] = useState<{ summary: string | null; message_count: number } | null>(null);
  const [showMemory, setShowMemory] = useState(false);

  // Chat hook
  const {
    messages,
    isStreaming,
    error,
    loadMessages,
    sendMessage,
    stopGeneration,
    clearMessages,
  } = useChat({
    agent: agentType as AgentType,
    conversationId: currentConversationId,
    onMessageSent: () => {
      // Refresh memory after message sent
      if (agentType) {
        memoryService.get(agentType as AgentType).then(setMemory).catch(console.error);
      }
    },
  });

  // Redirect if invalid agent
  useEffect(() => {
    if (agent && !agentConfig) {
      navigate('/', { replace: true });
    }
  }, [agent, agentConfig, navigate]);

  // Load conversations
  const loadConversations = useCallback(async () => {
    if (!agentType) return;
    setConversationsLoading(true);
    try {
      const convs = await conversationService.list(agentType as AgentType);
      setConversations(convs);

      // Auto-select most recent conversation if none selected
      if (!currentConversationId && convs.length > 0) {
        setCurrentConversationId(convs[0].id);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    } finally {
      setConversationsLoading(false);
    }
  }, [agentType, currentConversationId]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load messages when conversation changes
  useEffect(() => {
    if (currentConversationId) {
      loadMessages();
    } else {
      clearMessages();
    }
    setSelectionMode(false);
    setSelectedMessages(new Set());
  }, [currentConversationId, loadMessages, clearMessages]);

  // Load memory
  useEffect(() => {
    if (agentType) {
      memoryService.get(agentType as AgentType).then(setMemory).catch(console.error);
    }
  }, [agentType]);

  // Handlers
  const handleCreateConversation = async () => {
    if (!agentType) return;
    const conv = await conversationService.create(agentType as AgentType);
    setConversations((prev) => [conv, ...prev]);
    setCurrentConversationId(conv.id);
  };

  const handleDeleteConversation = async (id: number) => {
    if (!agentType) return;
    await conversationService.delete(id, agentType as AgentType);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (currentConversationId === id) {
      setCurrentConversationId(null);
    }
  };

  const handleRenameConversation = async (id: number, title: string) => {
    if (!agentType) return;
    await conversationService.update(id, agentType as AgentType, title);
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title } : c))
    );
  };

  const handleToggleSelection = (messageId: number) => {
    setSelectedMessages((prev) => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  };

  const handleExportMarkdown = async () => {
    if (!currentConversationId || !agentType) return;
    await exportService.downloadMarkdown(currentConversationId, agentType as AgentType);
  };

  const handleShare = async () => {
    if (!currentConversationId || !agentType) return;
    const result = await exportService.createShareLink(currentConversationId, agentType as AgentType);
    const fullUrl = `${window.location.origin}${result.share_url}`;
    await navigator.clipboard.writeText(fullUrl);
    alert(`分享链接已复制到剪贴板！\n\n${fullUrl}\n\n链接将在7天后过期。`);
  };

  if (!agentConfig) {
    return null;
  }

  return (
    <Layout title={agentConfig.titleZh} agentColor={agentConfig.color}>
      <div className="flex h-[calc(100vh-4rem)]">
        {/* Sidebar toggle for mobile */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="fixed left-0 top-1/2 -translate-y-1/2 z-40 p-2 bg-white dark:bg-gray-800 rounded-r-lg shadow-lg lg:hidden"
          style={{ borderColor: agentConfig.color }}
        >
          {sidebarOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
        </button>

        {/* Sidebar */}
        <aside
          className={`${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          } fixed lg:relative lg:translate-x-0 z-30 w-72 h-full transition-transform duration-300 p-4`}
        >
          <ConversationList
            conversations={conversations}
            currentId={currentConversationId}
            onSelect={setCurrentConversationId}
            onCreate={handleCreateConversation}
            onDelete={handleDeleteConversation}
            onRename={handleRenameConversation}
            loading={conversationsLoading}
            agentColor={agentConfig.color}
          />

          {/* Memory panel */}
          {memory && (
            <div className="mt-4">
              <button
                onClick={() => setShowMemory(!showMemory)}
                className="w-full flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 rounded-xl shadow-lg text-sm"
              >
                <div className="flex items-center gap-2">
                  <Brain size={18} style={{ color: agentConfig.color }} />
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    长期记忆
                  </span>
                </div>
                <span className="text-xs text-gray-400">
                  {memory.message_count} 条消息
                </span>
              </button>

              {showMemory && memory.summary && (
                <div className="mt-2 p-4 bg-white dark:bg-gray-800 rounded-xl shadow-lg">
                  <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                    {memory.summary}
                  </p>
                </div>
              )}
            </div>
          )}
        </aside>

        {/* Main chat area */}
        <main className="flex-1 flex flex-col p-4">
          {/* Toolbar */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {selectionMode ? (
                <>
                  <span className="text-sm text-gray-500">
                    已选择 {selectedMessages.size} 条消息
                  </span>
                  <button
                    onClick={() => {
                      setSelectionMode(false);
                      setSelectedMessages(new Set());
                    }}
                    className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <X size={18} />
                  </button>
                </>
              ) : (
                currentConversationId && (
                  <button
                    onClick={() => setSelectionMode(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    <CheckSquare size={16} />
                    选择消息
                  </button>
                )
              )}
            </div>

            {currentConversationId && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleExportMarkdown}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  title="导出 Markdown"
                >
                  <Download size={18} />
                </button>
                <button
                  onClick={handleShare}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  title="分享对话"
                >
                  <Share2 size={18} />
                </button>
              </div>
            )}
          </div>

          {/* Chat container */}
          <div className="flex-1">
            <ChatContainer
              messages={messages}
              isStreaming={isStreaming}
              error={error}
              onSend={sendMessage}
              onStop={stopGeneration}
              agentColor={agentConfig.color}
              greeting={agentConfig.greeting}
              disabled={!currentConversationId}
              selectedMessages={selectedMessages}
              selectionMode={selectionMode}
              onToggleSelection={handleToggleSelection}
            />
          </div>
        </main>
      </div>
    </Layout>
  );
}
