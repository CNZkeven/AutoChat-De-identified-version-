import api from './api';
import type { MemorySummary, MemoryOverview, AgentType } from '../types';

export const memoryService = {
  async get(agent: AgentType): Promise<MemorySummary> {
    const response = await api.get<MemorySummary>(`/api/memory/${agent}`);
    return response.data;
  },

  async regenerate(agent: AgentType): Promise<{ success: boolean; summary: string | null; message: string }> {
    const response = await api.post(`/api/memory/${agent}/regenerate`);
    return response.data;
  },

  async clear(agent: AgentType): Promise<{ success: boolean; message: string }> {
    const response = await api.delete(`/api/memory/${agent}`);
    return response.data;
  },

  async listAll(): Promise<MemoryOverview> {
    const response = await api.get<MemoryOverview>('/api/memory');
    return response.data;
  },
};
