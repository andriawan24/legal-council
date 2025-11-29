import { useState, useCallback } from 'react';
import { apiService } from '@/services/api';
import { SendMessageRequest, StreamChunk } from '@/types/api';
import { DeliberationMessage } from '@/types/legal-council';
import { normalizeMessage, normalizeMessages } from '@/lib/mappers';

export function useDeliberation(sessionId: string, initialMessages: DeliberationMessage[] = []) {
  const [messages, setMessages] = useState<DeliberationMessage[]>(initialMessages);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (data: SendMessageRequest) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.sendMessage(sessionId, data);
      setMessages(prev => [
        ...prev,
        normalizeMessage(response.user_message as any),
        ...normalizeMessages(response.agent_responses as any),
      ]);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const sendMessageStreaming = useCallback(async (data: SendMessageRequest) => {
    setStreaming(true);
    setError(null);

    // Temporary storage for the agent message being built
    let currentAgentMessage: Partial<DeliberationMessage> = {};

    await apiService.streamMessagesWithFetch(
      sessionId,
      data,
      (chunk: StreamChunk) => {
        switch (chunk.type) {
          case 'user_message':
            // Add user message immediately
            setMessages(prev => [
              ...prev, 
              {
                id: chunk.id,
                sender: 'user',
                sender_name: 'You (Presiding Judge)', // Or handle this mapping elsewhere
                content: chunk.content,
                timestamp: new Date(),
              } as DeliberationMessage
            ]);
            break;
          case 'agent_start':
            currentAgentMessage = {
              id: `temp-${chunk.agent_id}-${Date.now()}`,
              sender: chunk.agent_id,
              sender_name: chunk.agent_name,
              content: '',
              timestamp: new Date(),
            };
            setMessages(prev => [...prev, currentAgentMessage as DeliberationMessage]);
            break;
          case 'agent_chunk':
            setMessages(prev => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              // Check if the last message is from the same agent to append
              if (updated[lastIdx]?.sender === chunk.agent_id) {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: updated[lastIdx].content + chunk.content,
                };
              }
              return updated;
            });
            break;
          case 'agent_complete':
            setMessages(prev => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (updated[lastIdx]?.sender === chunk.agent_id) {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  id: chunk.message_id,
                  // Convert citation format if needed
                  cited_articles: chunk.citations?.laws?.map(l => ({ article: l, law_name: l, full_citation: l, law_number: null, law_year: null })) || [],
                  // referencing precedents might need mapping too
                };
              }
              return updated;
            });
            break;
        }
      },
      () => setStreaming(false),
      (err) => {
        setError(err.message);
        setStreaming(false);
      }
    );
  }, [sessionId]);

  const loadMessages = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiService.getMessages(sessionId);
      setMessages(normalizeMessages(response.messages as any));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load messages');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  return {
    messages,
    setMessages,
    loading,
    streaming,
    error,
    sendMessage,
    sendMessageStreaming,
    loadMessages,
  };
}
