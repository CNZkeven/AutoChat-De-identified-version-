import api from './api';
import type {
  UserAcademicReport,
  UserCourse,
  UserCourseObjective,
  UserCourseReport,
  UserGraduationRequirement,
  UserProfile,
} from '../types';

export const profileService = {
  async getPublicProfile(): Promise<UserProfile> {
    const response = await api.get<UserProfile>('/api/profile/public');
    return response.data;
  },

  async generatePublicProfile(): Promise<UserProfile> {
    const response = await api.post<UserProfile>('/api/profile/public');
    return response.data;
  },

  async listAcademics(): Promise<UserCourse[]> {
    const response = await api.get<UserCourse[]>('/api/profile/academics');
    return response.data;
  },

  async listCourseObjectives(offeringId: number): Promise<UserCourseObjective[]> {
    const response = await api.get<UserCourseObjective[]>(
      `/api/profile/courses/${offeringId}/objectives`
    );
    return response.data;
  },

  async getCourseReport(offeringId: number): Promise<UserCourseReport> {
    const response = await api.get<UserCourseReport>(`/api/profile/courses/${offeringId}/report`);
    return response.data;
  },

  async generateCourseReport(offeringId: number): Promise<UserCourseReport> {
    const response = await api.post<UserCourseReport>(`/api/profile/courses/${offeringId}/report`);
    return response.data;
  },

  async getGraduationRequirements(): Promise<UserGraduationRequirement> {
    const response = await api.get<UserGraduationRequirement>('/api/profile/graduation-requirements');
    return response.data;
  },

  async refreshGraduationRequirements(): Promise<UserGraduationRequirement> {
    const response = await api.post<UserGraduationRequirement>(
      '/api/profile/graduation-requirements/refresh'
    );
    return response.data;
  },

  async getAcademicReport(): Promise<UserAcademicReport> {
    const response = await api.get<UserAcademicReport>('/api/profile/academic-report');
    return response.data;
  },

  async generateAcademicReport(): Promise<UserAcademicReport> {
    const response = await api.post<UserAcademicReport>('/api/profile/academic-report');
    return response.data;
  },
};
