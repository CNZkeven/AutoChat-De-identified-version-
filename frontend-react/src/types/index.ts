// Agent types
export type AgentType = 'ideological' | 'evaluation' | 'task' | 'exploration' | 'competition' | 'course';

export interface AgentStyleOption {
  id: string;
  name: string;
  description: string;
  prompt: string;
}

export interface AgentConfig {
  type: AgentType;
  title: string;
  titleZh: string;
  description: string;
  color: string;
  colorDark: string;
  colorLight: string;
  backgroundImage: string;
  greeting: string;
  styles: AgentStyleOption[];
}

// User and Auth types
export interface User {
  id: number;
  username: string;
  email?: string | null;
  full_name?: string | null;
  major?: string | null;
  grade?: number | null;
  gender?: string | null;
}

export interface AdminUser extends User {
  is_active?: boolean | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// Conversation types
export interface Conversation {
  id: number;
  title: string;
  agent: AgentType;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AdminConversation extends Omit<Conversation, 'agent'> {
  agent: string;
  user_id: number;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

// Memory types
export interface MemorySummary {
  summary: string | null;
  message_count: number;
  updated_at: string | null;
}

export interface MemoryOverview {
  [agent: string]: {
    has_memory: boolean;
    summary_preview: string | null;
    message_count: number;
    updated_at: string | null;
  };
}

// Export types
export interface ShareLink {
  token: string;
  share_url: string;
  is_active: boolean;
  expires_at: string | null;
  view_count: number;
  created_at: string | null;
}

export interface SharedConversation {
  title: string;
  agent: string;
  agent_name: string;
  created_at: string;
  messages: Message[];
}

// API response types
export interface ApiError {
  detail: string;
}

// Chat request types
export interface ChatRequest {
  conversation_id: number | null;
  message?: string;
  messages?: { role: 'system' | 'user' | 'assistant'; content: string }[];
  selected_messages?: { role: 'user' | 'assistant'; content: string }[];
}

export interface AdminAgent {
  id: string;
  title: string;
  greeting?: string | null;
  profile?: Record<string, unknown> | null;
  prompt?: string | null;
  prompt_template_path?: string | null;
}

export interface AdminUserProfile {
  user_id: number;
  data: Record<string, unknown>;
}

export interface AdminUserProfiles {
  user_id: number;
  system_profile?: string | null;
  public_profile?: string | null;
  system_updated_at?: string | null;
  public_updated_at?: string | null;
}

export interface UserCourse {
  offering_id: number;
  class_number?: string | null;
  course_code: string;
  course_name: string;
  teacher_name?: string | null;
  total_score?: number | null;
  grade_text?: string | null;
  percentile?: number | null;
}

export interface UserCourseObjective {
  objective_id: number;
  objective_index?: string | null;
  description: string;
  achievement_score?: number | null;
  total_score?: number | null;
  max_score?: number | null;
  percentile?: number | null;
}

export interface UserCourseReport {
  content?: string | null;
  updated_at?: string | null;
}

export interface UserProfile {
  content?: string | null;
  updated_at?: string | null;
}

export interface UserGraduationRequirement {
  data: Record<string, unknown>;
  updated_at?: string | null;
}

export interface UserAcademicReport {
  content?: string | null;
  updated_at?: string | null;
}

export interface AdminRunSummary {
  id: number;
  agent_run_id?: number | null;
  conversation_id?: number | null;
  user_message_id?: number | null;
  request_text?: string | null;
  created_at?: string | null;
}

export interface AdminRunDetail extends AdminRunSummary {
  trace: Array<Record<string, unknown>>;
}

export interface AdminDebugRunRequest {
  user_id: number;
  agent: string;
  conversation_id?: number | null;
  messages?: { role: 'system' | 'user' | 'assistant'; content: string }[];
  selected_messages?: { role: 'user' | 'assistant'; content: string }[];
}

export interface AdminDebugRunResponse {
  conversation_id: number;
  trace_id: number;
  final_text?: string | null;
}
