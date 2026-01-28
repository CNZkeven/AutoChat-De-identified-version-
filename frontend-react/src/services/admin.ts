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
  AdminUserProfiles,
  UserCourse,
  UserCourseObjective,
  UserCourseReport,
} from '../types';

export const adminService = {
  async me(): Promise<AdminUser> {
    const response = await api.get<AdminUser>('/api/admin/me');
    return response.data;
  },

  async listUsers(params?: {
    q?: string;
    major?: string;
    grade?: number | null;
    gender?: string;
  }): Promise<AdminUser[]> {
    const response = await api.get<AdminUser[]>('/api/admin/users', { params });
    return response.data;
  },

  async getUserProfile(userId: number): Promise<AdminUserProfile> {
    const response = await api.get<AdminUserProfile>(`/api/admin/users/${userId}/profile`);
    return response.data;
  },

  async getUser(userId: number): Promise<AdminUser> {
    const response = await api.get<AdminUser>(`/api/admin/users/${userId}`);
    return response.data;
  },

  async getUserProfiles(userId: number): Promise<AdminUserProfiles> {
    const response = await api.get<AdminUserProfiles>(`/api/admin/users/${userId}/profiles`);
    return response.data;
  },

  async listUserFilters(): Promise<{ majors: string[]; grades: number[]; genders: string[] }> {
    const response = await api.get<{ majors: string[]; grades: number[]; genders: string[] }>(
      '/api/admin/users/filters'
    );
    return response.data;
  },

  async updateUser(
    userId: number,
    payload: Partial<{
      email: string | null;
      full_name: string | null;
      major: string | null;
      grade: number | null;
      gender: string | null;
      is_active: boolean | null;
    }>
  ): Promise<AdminUser> {
    const response = await api.patch<AdminUser>(`/api/admin/users/${userId}`, payload);
    return response.data;
  },

  async resetUserPassword(userId: number): Promise<void> {
    await api.post(`/api/admin/users/${userId}/reset-password`);
  },

  async downloadImportTemplate(): Promise<Blob> {
    const response = await api.get('/api/admin/users/import-template', { responseType: 'blob' });
    return response.data;
  },

  async importUsers(file: File): Promise<{ total: number; created: number; updated: number; failed: number }> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/api/admin/users/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async listUserAcademics(userId: number): Promise<UserCourse[]> {
    const response = await api.get<UserCourse[]>(`/api/admin/users/${userId}/academics`);
    return response.data;
  },

  async listUserCourseObjectives(userId: number, offeringId: number): Promise<UserCourseObjective[]> {
    const response = await api.get<UserCourseObjective[]>(
      `/api/admin/users/${userId}/courses/${offeringId}/objectives`
    );
    return response.data;
  },

  async getUserCourseReport(userId: number, offeringId: number): Promise<UserCourseReport> {
    const response = await api.get<UserCourseReport>(
      `/api/admin/users/${userId}/courses/${offeringId}/report`
    );
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
