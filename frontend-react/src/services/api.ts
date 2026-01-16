import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { API_BASE_URL } from '../utils/constants';
import { useAuthStore } from '../store/authStore';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().token;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// Helper function for SSE requests
export async function fetchSSE(
  url: string,
  options: {
    method?: string;
    body?: object;
    onMessage: (data: { content?: string; error?: string }) => void;
    onError?: (error: Error) => void;
    onComplete?: () => void;
    signal?: AbortSignal;
  }
): Promise<void> {
  const token = useAuthStore.getState().token;

  try {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      method: options.method || 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        Authorization: token ? `Bearer ${token}` : '',
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    });

    if (!response.ok) {
      let detail = '';
      try {
        const data = await response.json();
        detail = (data as { detail?: string; error?: string })?.detail || (data as { error?: string })?.error || '';
      } catch {
        // ignore parse errors
      }
      throw new Error(detail || `HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No response body');
    }

    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        options.onComplete?.();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            options.onMessage(data);
          } catch {
            // Ignore parse errors for incomplete chunks
          }
        }
      }
    }
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      return;
    }
    options.onError?.(error instanceof Error ? error : new Error('Unknown error'));
  }
}
