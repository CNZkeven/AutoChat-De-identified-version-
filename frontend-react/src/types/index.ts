// Agent types
export type AgentType = 'ideological' | 'evaluation' | 'task' | 'exploration' | 'competition' | 'course';

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
}

// User and Auth types
export interface User {
  id: number;
  username: string;
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
  conversation_id: number;
  message?: string;
  messages?: { role: string; content: string }[];
  selected_messages?: { role: string; content: string }[];
}
