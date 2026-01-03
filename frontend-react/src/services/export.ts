import api from './api';
import { API_BASE_URL } from '../utils/constants';
import { useAuthStore } from '../store/authStore';
import type { ShareLink, SharedConversation, AgentType } from '../types';

export const exportService = {
  async downloadMarkdown(conversationId: number, agent: AgentType): Promise<void> {
    const token = useAuthStore.getState().token;
    const url = `${API_BASE_URL}/api/export/conversation/${conversationId}/markdown?agent=${agent}`;

    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to download markdown');
    }

    // Get filename from Content-Disposition header or use default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'conversation.md';
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/);
      if (match) {
        filename = match[1];
      }
    }

    // Create blob and download
    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(blobUrl);
  },

  async createShareLink(
    conversationId: number,
    agent: AgentType,
    expiresDays: number = 7
  ): Promise<{ share_url: string; share_token: string; expires_at: string }> {
    const response = await api.post(
      `/api/export/conversation/${conversationId}/share?agent=${agent}`,
      { expires_days: expiresDays }
    );
    return response.data;
  },

  async getSharedConversation(token: string): Promise<SharedConversation> {
    const response = await api.get<SharedConversation>(`/api/export/shared/${token}`);
    return response.data;
  },

  async revokeShareLink(token: string): Promise<{ success: boolean; message: string }> {
    const response = await api.delete(`/api/export/share/${token}`);
    return response.data;
  },

  async listShareLinks(conversationId: number, agent: AgentType): Promise<ShareLink[]> {
    const response = await api.get<ShareLink[]>(
      `/api/export/conversation/${conversationId}/shares?agent=${agent}`
    );
    return response.data;
  },
};
