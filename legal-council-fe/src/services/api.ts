import { config } from '@/lib/config';
import {
  CreateSessionRequest,
  CreateSessionResponse,
  SessionResponse,
  ListSessionsResponse,
  SendMessageRequest,
  SendMessageResponse,
  GetMessagesResponse,
  StreamChunk,
  GenerateOpinionResponse,
  SearchCasesRequest,
  SearchCasesResponse,
  CaseResponse,
  CaseStatisticsResponse,
} from '@/types/api';

const API_BASE_URL = config.api.baseUrl;

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    // Remove trailing slash from base URL if present and leading slash from endpoint if present
    const normalizedBase = this.baseUrl.endsWith('/') ? this.baseUrl.slice(0, -1) : this.baseUrl;
    const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${normalizedBase}${normalizedEndpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  // Health
  async getHealth() {
    return this.request<{ status: string }>('/health');
  }

  // Sessions
  async createSession(data: CreateSessionRequest) {
    return this.request<CreateSessionResponse>('/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getSession(sessionId: string) {
    return this.request<SessionResponse>(`/sessions/${sessionId}`);
  }

  async listSessions(limit = 10, page = 1) {
    return this.request<ListSessionsResponse>(`/sessions?limit=${limit}&page=${page}`);
  }

  async archiveSession(sessionId: string) {
    return this.request<void>(`/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  // Messages
  async sendMessage(sessionId: string, data: SendMessageRequest) {
    return this.request<SendMessageResponse>(`/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMessages(sessionId: string, limit = 50) {
    return this.request<GetMessagesResponse>(`/sessions/${sessionId}/messages?limit=${limit}`);
  }

  // Streaming
  streamMessages(sessionId: string, data: SendMessageRequest): EventSource {
    const normalizedBase = this.baseUrl.endsWith('/') ? this.baseUrl.slice(0, -1) : this.baseUrl;
    const url = `${normalizedBase}/sessions/${sessionId}/messages/stream`;
    return new EventSource(url);
  }

  async streamMessagesWithFetch(
    sessionId: string,
    data: SendMessageRequest,
    onChunk: (chunk: StreamChunk) => void,
    onComplete: () => void,
    onError: (error: Error) => void
  ) {
    const normalizedBase = this.baseUrl.endsWith('/') ? this.baseUrl.slice(0, -1) : this.baseUrl;
    const url = `${normalizedBase}/sessions/${sessionId}/messages/stream`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep the last line in buffer as it might be incomplete
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!trimmedLine || trimmedLine === ': ping') continue;

          if (trimmedLine.startsWith('data: ')) {
            try {
              const jsonStr = trimmedLine.slice(6);
              const data = JSON.parse(jsonStr);
              onChunk(data);
            } catch (e) {
              console.warn('Failed to parse SSE data:', trimmedLine, e);
            }
          }
        }
      }
      
      // Process any remaining buffer
      if (buffer.trim().startsWith('data: ')) {
         try {
            const jsonStr = buffer.trim().slice(6);
            const data = JSON.parse(jsonStr);
            onChunk(data);
         } catch (e) {
             // ignore trailing incomplete data
         }
      }

      onComplete();
    } catch (error) {
      console.error('Streaming error:', error);
      onError(error instanceof Error ? error : new Error(String(error)));
    }
  }

  // Opinion
  async generateOpinion(sessionId: string) {
    return this.request<GenerateOpinionResponse>(`/sessions/${sessionId}/opinion`, {
      method: 'POST',
      body: JSON.stringify({ include_dissent: true }),
    });
  }

  async exportOpinion(sessionId: string, format: 'pdf' | 'docx') {
    const normalizedBase = this.baseUrl.endsWith('/') ? this.baseUrl.slice(0, -1) : this.baseUrl;
    const url = `${normalizedBase}/sessions/${sessionId}/opinion/export?format=${format}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Export failed: ${response.status}`);
    return response.blob();
  }

  // Cases
  async searchCases(data: SearchCasesRequest) {
    return this.request<SearchCasesResponse>('/cases/search', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getCase(caseId: string) {
    return this.request<CaseResponse>(`/cases/${caseId}`);
  }

  async getCaseStatistics(caseType?: string, substanceType?: string) {
    const params = new URLSearchParams();
    if (caseType) params.set('case_type', caseType);
    if (substanceType) params.set('substance_type', substanceType);
    return this.request<CaseStatisticsResponse>(`/cases/statistics?${params}`);
  }
}

export const apiService = new ApiService(API_BASE_URL);
