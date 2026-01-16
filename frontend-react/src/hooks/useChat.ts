import { useState, useCallback, useRef } from 'react';
import { fetchSSE } from '../services/api';
import { conversationService } from '../services/conversations';
import type { Message, AgentType } from '../types';

interface UseChatOptions {
  agent: AgentType;
  conversationId: number | null;
  isGuest?: boolean;
  onMessageSent?: () => void;
}

interface SendMessageOptions {
  systemPrompt?: string;
}

export function useChat({ agent, conversationId, isGuest = false, onMessageSent }: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamingMessageRef = useRef<string>('');

  // Load messages for a conversation
  const loadMessages = useCallback(async () => {
    if (!conversationId || isGuest) {
      setMessages([]);
      return;
    }

    try {
      const msgs = await conversationService.getMessages(conversationId, agent);
      setMessages(msgs);
    } catch (err) {
      console.error('Failed to load messages:', err);
      setError('加载消息失败');
    }
  }, [conversationId, agent]);

  // Send a message
  const sendMessage = useCallback(
    async (content: string, selectedMessages?: Message[], options?: SendMessageOptions) => {
      if ((!conversationId && !isGuest) || isStreaming || !content.trim()) return;

      const userMessage: Message = {
        id: Date.now(),
        role: 'user',
        content: content.trim(),
        created_at: new Date().toISOString(),
      };

      // Add user message to UI immediately
      setMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);
      setError(null);
      streamingMessageRef.current = '';

      // Add placeholder for assistant message
      const assistantId = Date.now() + 1;
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          created_at: new Date().toISOString(),
        },
      ]);

      abortRef.current = new AbortController();

      try {
        const payloadMessages = [...messages, userMessage].map((m) => ({
          role: m.role,
          content: m.content,
        }));
        const finalMessages = options?.systemPrompt
          ? [{ role: 'system', content: options.systemPrompt }, ...payloadMessages]
          : payloadMessages;

        await fetchSSE(`/api/agents/${agent}/chat`, {
          method: 'POST',
          body: {
            conversation_id: conversationId,
            messages: finalMessages,
            selected_messages: selectedMessages?.map((m) => ({
              role: m.role,
              content: m.content,
            })),
          },
          signal: abortRef.current.signal,
          onMessage: (data) => {
            if (data.content) {
              streamingMessageRef.current += data.content;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: streamingMessageRef.current }
                    : m
                )
              );
            }
            if (data.error) {
              setError(data.error);
            }
          },
          onError: (err) => {
            setError(err.message);
          },
          onComplete: () => {
            onMessageSent?.();
          },
        });
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [agent, conversationId, messages, isStreaming, onMessageSent, isGuest]
  );

  // Stop generation
  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    setMessages,
    isStreaming,
    error,
    loadMessages,
    sendMessage,
    stopGeneration,
    clearMessages,
  };
}
