import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { ChatContainer } from '../components/chat/ChatContainer';
import { ConversationList } from '../components/conversation/ConversationList';
import { useChat } from '../hooks/useChat';
import { conversationService } from '../services/conversations';
import { getAgentConfig } from '../utils/constants';
import { memoryService } from '../services/memory';
import { exportService } from '../services/export';
import { useAuthStore } from '../store/authStore';
import {
  Brain,
  Download,
  Share2,
  CheckSquare,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import type { Conversation, AgentType, Message } from '../types';

export function ChatPage() {
  const { agent } = useParams<{ agent: string }>();
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isGuest = !isAuthenticated;

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
  const [draftMessage, setDraftMessage] = useState('');

  const [styleByConversation, setStyleByConversation] = useState<Record<string, string>>({});
  const [lastAppliedStyleByConversation, setLastAppliedStyleByConversation] = useState<Record<string, string>>({});

  const conversationKey = useMemo(() => {
    if (!agentType) return '';
    return `${agentType}:${isGuest ? 'guest' : currentConversationId ?? 'none'}`;
  }, [agentType, currentConversationId, isGuest]);
  const styleOptions = agentConfig?.styles || [];
  const defaultStyleId = styleOptions[0]?.id;
  const selectedStyleId = conversationKey ? styleByConversation[conversationKey] || defaultStyleId : defaultStyleId;
  const selectedStyle = styleOptions.find((style) => style.id === selectedStyleId);

  // Memory state
  const [memory, setMemory] = useState<{ summary: string | null; message_count: number } | null>(null);
  const [showMemory, setShowMemory] = useState(false);

  // Redirect if invalid agent
  useEffect(() => {
    if (agent && !agentConfig) {
      navigate('/', { replace: true });
    }
  }, [agent, agentConfig, navigate]);

  useEffect(() => {
    if (!conversationKey || !defaultStyleId) return;
    const stored = window.localStorage.getItem(`style:${conversationKey}`);
    const nextStyle = stored || defaultStyleId;
    setStyleByConversation((prev) =>
      prev[conversationKey] ? prev : { ...prev, [conversationKey]: nextStyle }
    );
  }, [conversationKey, defaultStyleId]);

  // Load conversations
  const loadConversations = useCallback(async () => {
    if (!agentType) return;
    if (isGuest) {
      setConversations([]);
      setConversationsLoading(false);
      return;
    }
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
  }, [agentType, currentConversationId, isGuest]);

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
    isGuest,
    onMessageSent: () => {
      // Refresh memory after message sent
      if (agentType && !isGuest) {
        memoryService.get(agentType as AgentType).then(setMemory).catch(console.error);
        loadConversations();
      }
    },
  });

  useEffect(() => {
    if (!conversationKey || !selectedStyleId) return;
    if (messages.length > 0 && !lastAppliedStyleByConversation[conversationKey]) {
      setLastAppliedStyleByConversation((prev) => ({
        ...prev,
        [conversationKey]: selectedStyleId,
      }));
    }
  }, [conversationKey, selectedStyleId, messages.length, lastAppliedStyleByConversation]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load messages when conversation changes
  useEffect(() => {
    if (isGuest) {
      return;
    }
    if (currentConversationId) {
      loadMessages();
    } else {
      clearMessages();
    }
    setSelectionMode(false);
    setSelectedMessages(new Set());
  }, [currentConversationId, loadMessages, clearMessages, isGuest]);

  // Load memory
  useEffect(() => {
    if (agentType && !isGuest) {
      memoryService.get(agentType as AgentType).then(setMemory).catch(console.error);
    }
  }, [agentType, isGuest]);

  // Handlers
  const handleCreateConversation = async () => {
    if (!agentType) return;
    if (isGuest) {
      clearMessages();
      setSelectedMessages(new Set());
      setSelectionMode(false);
      setDraftMessage('');
      return;
    }
    const conv = await conversationService.create(agentType as AgentType);
    setConversations((prev) => [conv, ...prev]);
    setCurrentConversationId(conv.id);
  };

  const handleDeleteConversation = async (id: number) => {
    if (!agentType) return;
    if (isGuest) return;
    await conversationService.delete(id, agentType as AgentType);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (currentConversationId === id) {
      setCurrentConversationId(null);
    }
  };

  const handleRenameConversation = async (id: number, title: string) => {
    if (!agentType) return;
    if (isGuest) return;
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

  const handleStyleChange = (styleId: string) => {
    if (!conversationKey) return;
    setStyleByConversation((prev) => ({ ...prev, [conversationKey]: styleId }));
    window.localStorage.setItem(`style:${conversationKey}`, styleId);
  };

  const handleUseSelectedPrompt = () => {
    if (!selectedMessages.size) return;
    const selected = messages.filter((m) => selectedMessages.has(m.id));
    if (!selected.length) return;
    const formatted = selected
      .map((m) => `${m.role === 'user' ? '用户' : agentConfig?.titleZh || '智能体'}：${m.content}`)
      .join('\n');
    const hint = `请结合以下选中的对话内容：\n${formatted}\n`;
    setDraftMessage((prev) => (prev ? `${prev}\n\n${hint}` : hint));
  };

  const handleSendMessage = (content: string, selected?: Message[]) => {
    if (!selectedStyle || !conversationKey) {
      sendMessage(content, selected);
      return;
    }
    const lastAppliedStyle = lastAppliedStyleByConversation[conversationKey];
    const shouldInjectStyle =
      messages.length === 0 || (!lastAppliedStyle || lastAppliedStyle !== selectedStyle.id);
    const systemPrompt = shouldInjectStyle ? selectedStyle.prompt : undefined;

    if (shouldInjectStyle) {
      setLastAppliedStyleByConversation((prev) => ({
        ...prev,
        [conversationKey]: selectedStyle.id,
      }));
    }

    sendMessage(content, selected, { systemPrompt });
  };

  const handleExportMarkdown = async () => {
    if (!currentConversationId || !agentType || isGuest) return;
    await exportService.downloadMarkdown(currentConversationId, agentType as AgentType);
  };

  const handleShare = async () => {
    if (!currentConversationId || !agentType || isGuest) return;
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
          {isGuest ? (
            <div className="p-4 bg-white dark:bg-gray-800 rounded-xl shadow-lg text-sm text-gray-600 dark:text-gray-400">
              <p className="font-medium text-gray-700 dark:text-gray-300 mb-2">
                访客模式
              </p>
              <p>可直接对话，但不会保存会话、记忆或分享记录。</p>
            </div>
          ) : (
            <>
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
            </>
          )}
        </aside>

        {/* Main chat area */}
        <main className="flex-1 flex flex-col p-4">
          {styleOptions.length > 0 && (
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <span className="text-sm text-gray-600 dark:text-gray-400">回复风格</span>
              <select
                value={selectedStyleId || ''}
                onChange={(e) => handleStyleChange(e.target.value)}
                className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200"
              >
                {styleOptions.map((style) => (
                  <option key={style.id} value={style.id}>
                    {style.name}
                  </option>
                ))}
              </select>
              {selectedStyle?.description && (
                <span className="text-xs text-gray-400">{selectedStyle.description}</span>
              )}
              {messages.length > 0 &&
                selectedStyle &&
                lastAppliedStyleByConversation[conversationKey] !== selectedStyle.id && (
                  <span className="text-xs text-amber-500">下次发送将切换风格</span>
                )}
            </div>
          )}

          {/* Toolbar */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {selectionMode ? (
                <>
                  <span className="text-sm text-gray-500">
                    已选择 {selectedMessages.size} 条消息
                  </span>
                  <button
                    onClick={handleUseSelectedPrompt}
                    disabled={selectedMessages.size === 0}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    用勾选生成提示
                  </button>
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
                messages.length > 0 && (
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

            {currentConversationId && !isGuest && (
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
              onSend={handleSendMessage}
              onStop={stopGeneration}
              agentColor={agentConfig.color}
              greeting={agentConfig.greeting}
              disabled={isAuthenticated && !currentConversationId}
              selectedMessages={selectedMessages}
              selectionMode={selectionMode}
              onToggleSelection={handleToggleSelection}
              draftMessage={draftMessage}
              onDraftChange={setDraftMessage}
            />
          </div>
        </main>
      </div>
    </Layout>
  );
}
