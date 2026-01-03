import api from './api';
import type { Conversation, Message, AgentType } from '../types';

export const conversationService = {
  async list(agent: AgentType): Promise<Conversation[]> {
    const response = await api.get<Conversation[]>(`/api/conversations?agent=${agent}`);
    return response.data;
  },

  async create(agent: AgentType, title?: string): Promise<Conversation> {
    const response = await api.post<Conversation>(`/api/conversations?agent=${agent}`, {
      title: title || '新对话',
    });
    return response.data;
  },

  async update(id: number, agent: AgentType, title: string): Promise<Conversation> {
    const response = await api.patch<Conversation>(`/api/conversations/${id}?agent=${agent}`, {
      title,
    });
    return response.data;
  },

  async delete(id: number, agent: AgentType): Promise<void> {
    await api.delete(`/api/conversations/${id}?agent=${agent}`);
  },

  async getMessages(conversationId: number, agent: AgentType): Promise<Message[]> {
    const response = await api.get<Message[]>(
      `/api/conversations/${conversationId}/messages?agent=${agent}`
    );
    return response.data;
  },
};
