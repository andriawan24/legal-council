import { CaseRecord, CaseSearchFilters } from '@/types/legal-council';
import { config } from '@/lib/config';

const API_BASE_URL = config.api.baseUrl;

type ApiConfig = {
  headers?: Record<string, string>;
};

class ApiService {
  private baseUrl: string;
  private config: ApiConfig;

  constructor(baseUrl: string, config: ApiConfig = {}) {
    this.baseUrl = baseUrl;
    this.config = {
      headers: {
        'Content-Type': 'application/json',
        ...config.headers,
      },
    };
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      ...this.config.headers,
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`Request failed for ${url}:`, error);
      throw error;
    }
  }

  async getHealth(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health');
  }

  async searchCases(filters: CaseSearchFilters): Promise<CaseRecord[]> {
    const searchParams = new URLSearchParams();
    if (filters.crime_category) searchParams.set('category', filters.crime_category);

    return this.request<CaseRecord[]>(`/cases?${searchParams.toString()}`);
  }

  async createCase(caseData: Partial<CaseRecord>): Promise<CaseRecord> {
    return this.request<CaseRecord>('/cases', {
      method: 'POST',
      body: JSON.stringify(caseData),
    });
  }
}

// Export a singleton instance
export const apiService = new ApiService(API_BASE_URL);
