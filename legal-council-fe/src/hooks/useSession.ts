import { useState, useCallback } from 'react';
import { apiService } from '@/services/api';
import { CreateSessionRequest, DeliberationSessionResponse } from '@/types/api';

export function useSession() {
  const [session, setSession] = useState<DeliberationSessionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createSession = useCallback(async (data: CreateSessionRequest) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.createSession(data);
      // Return CreateSessionResponse directly - caller handles navigation
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSession = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getSession(sessionId);
      // Extract session from wrapped response
      setSession(response.session);
      return response.session;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { session, loading, error, createSession, loadSession };
}

