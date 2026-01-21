import api from './api';
import type {
  AdminAgent,
  AdminConversation,
  AdminDebugRunRequest,
  AdminDebugRunResponse,
  AdminRunDetail,
  AdminRunSummary,
  AdminUser,
  AdminUserProfile,
} from '../types';

export const adminService = {
  async me(): Promise<AdminUser> {
    const response = await api.get<AdminUser>('/api/admin/me');
    return response.data;
  },

  async listUsers(query?: string): Promise<AdminUser[]> {
    const response = await api.get<AdminUser[]>('/api/admin/users', {
      params: query ? { q: query } : undefined,
    });
    return response.data;
  },

  async getUserProfile(userId: number): Promise<AdminUserProfile> {
    const response = await api.get<AdminUserProfile>(`/api/admin/users/${userId}/profile`);
    return response.data;
  },

  async listAgents(): Promise<AdminAgent[]> {
    const response = await api.get<AdminAgent[]>('/api/admin/agents');
    return response.data;
  },

  async listConversations(userId: number, agent: string): Promise<AdminConversation[]> {
    const response = await api.get<AdminConversation[]>(
      `/api/admin/users/${userId}/agents/${agent}/conversations`
    );
    return response.data;
  },

  async listRuns(conversationId: number): Promise<AdminRunSummary[]> {
    const response = await api.get<AdminRunSummary[]>(
      `/api/admin/conversations/${conversationId}/runs`
    );
    return response.data;
  },

  async getRunDetail(traceId: number): Promise<AdminRunDetail> {
    const response = await api.get<AdminRunDetail>(`/api/admin/runs/${traceId}`);
    return response.data;
  },

  async debugRun(payload: AdminDebugRunRequest): Promise<AdminDebugRunResponse> {
    const response = await api.post<AdminDebugRunResponse>('/api/admin/debug/run', payload);
    return response.data;
  },
};
