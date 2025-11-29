'use client';

import type React from 'react';
import { useState, useRef, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { AgentAvatar } from './agent-avatar';
import { Loader2, Send, Gavel, HelpCircle, AlertCircle } from 'lucide-react';
import { MessageBubble } from './message-bubble';
import { useDeliberation } from '@/hooks/useDeliberation';
import { useLegalCouncil } from '@/context/legal-council-context';
import { apiService } from '@/services/api';
import { DeliberationMessage, LegalOpinionDraft, CouncilMemberRole } from '@/types/legal-council';
import { AgentId } from '@/types/api';

interface CouncilDebateProps {
  caseFacts: string;
  onComplete: (messages: DeliberationMessage[], opinion: LegalOpinionDraft) => void;
}

const AGENTS = {
  strict: {
    name: 'Judge A - Strict Constructionist',
    shortName: 'Judge A',
    role: 'Strict Constructionist',
    id: 'strict' as CouncilMemberRole, // Mapping for display
  },
  humanist: {
    name: 'Judge B - Rehabilitative Approach',
    shortName: 'Judge B',
    role: 'Humanist',
    id: 'humanist' as CouncilMemberRole,
  },
  historian: {
    name: 'Judge C - Jurisprudence Expert',
    shortName: 'Judge C',
    role: 'Historian',
    id: 'historian' as CouncilMemberRole,
  },
  user: {
    name: 'You (Presiding Judge)',
    shortName: 'You',
    role: 'Presiding Judge',
    id: 'user' as const,
  },
  system: {
    name: 'System',
    shortName: 'System',
    role: 'System',
    id: 'system' as const,
  },
};

const QUICK_ACTIONS = [
  { label: "Ask Judge A's opinion", prompt: 'Judge A, what is your opinion on this case?' },
  {
    label: "Ask Judge B's opinion",
    prompt: 'Judge B, from a rehabilitation perspective, what is your view?',
  },
  {
    label: 'Ask about precedents',
    prompt: 'Judge C, are there any relevant precedents or jurisprudence for this case?',
  },
  { label: 'Request clarification', prompt: 'Could you elaborate more on the legal basis?' },
];

export function CouncilDebate({ caseFacts: _caseFacts, onComplete }: CouncilDebateProps) {
  const { sessionId, messages: contextMessages, setMessages: setContextMessages } = useLegalCouncil();
  
  const { 
    messages, 
    sendMessageStreaming, 
    loading: isSending, 
    streaming: isStreaming,
    loadMessages,
    error,
  } = useDeliberation(sessionId || '', contextMessages);

  // Sync local messages with context if needed
  // We sync only when local messages change and are different from context
  // This avoids the initial overwrite issue because useDeliberation starts with contextMessages
  useEffect(() => {
    if (messages.length !== contextMessages.length) {
      setContextMessages(messages);
    }
  }, [messages, setContextMessages, contextMessages.length]);

  // If for some reason we have no messages but valid session (e.g. page refresh), load them
  useEffect(() => {
    if (sessionId && messages.length === 0 && contextMessages.length === 0) {
      loadMessages();
    }
  }, [sessionId, messages.length, contextMessages.length, loadMessages]);

  const [userInput, setUserInput] = useState('');
  const [isGeneratingOpinion, setIsGeneratingOpinion] = useState(false);
  
  const isAgentTyping = isSending || isStreaming;
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAgentTyping]);

  const getTargetAgent = (userMessage: string): AgentId => {
    const msg = userMessage.toLowerCase();
    if (msg.includes('judge a') || msg.includes('strict')) return 'strict' as unknown as AgentId;
    if (msg.includes('judge b') || msg.includes('rehabilit') || msg.includes('humanis')) return 'humanist' as unknown as AgentId;
    if (msg.includes('judge c') || msg.includes('precedent') || msg.includes('historian')) return 'historian' as unknown as AgentId;
    return 'all';
  };

  const handleUserSubmit = async (text?: string) => {
    const messageText = text || userInput.trim();
    if (!messageText || isAgentTyping || !sessionId) return;

    setUserInput('');

    // Determine target agent based on content (simple heuristic)
    const targetAgent = getTargetAgent(messageText);

    try {
      // Send message using streaming hook
      await sendMessageStreaming({
        content: messageText,
        target_agent: targetAgent,
        intent: 'ask_opinion', // Changed from 'general' to 'ask_opinion' to match backend enum
      });
    } catch (e) {
      console.error("Failed to send message:", e);
      // error state is handled by hook
    }

    inputRef.current?.focus();
  };

  const handleQuickAction = (prompt: string) => {
    handleUserSubmit(prompt);
  };

  const handleGenerateOpinion = async () => {
    if (!sessionId) return;
    setIsGeneratingOpinion(true);
    try {
      const response = await apiService.generateOpinion(sessionId);
      onComplete(messages, response.opinion);
    } catch (error) {
      console.error('Failed to generate opinion:', error);
      // Handle error
    } finally {
      setIsGeneratingOpinion(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleUserSubmit();
    }
  };

  return (
    <div className='space-y-4'>
      <div className='flex items-center justify-center gap-6 py-3 px-4 bg-secondary rounded-lg'>
        <div className='flex items-center gap-2'>
          <AgentAvatar agent='user' size='sm' />
          <span className='text-xs text-foreground font-medium'>You (Presiding)</span>
        </div>
        <div className='w-px h-6 bg-border' />
        {(['strict', 'humanist', 'historian'] as const).map((agent) => (
          <div key={agent} className='flex items-center gap-2'>
            <AgentAvatar agent={agent} size='sm' />
            <span className='text-xs text-muted-foreground'>{AGENTS[agent].shortName}</span>
          </div>
        ))}
      </div>

      <Card className='bg-card border-border'>
        <CardContent className='p-0'>
          <div className='h-[450px] overflow-y-auto space-y-4 p-4'>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}

            {isAgentTyping && (
              <div className='flex gap-3 mx-6'>
                {/* We might not know exactly who is typing first in a group chat, defaulting to generic or last known */}
                <div className='flex-1 max-w-[80%]'>
                  <div className='bg-secondary rounded-lg rounded-tl-none p-3'>
                    <div className='text-sm text-foreground'>
                      <span className='flex items-center gap-1 text-muted-foreground'>
                        <Loader2 className='w-3 h-3 animate-spin' />
                        Council is deliberating...
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions */}
          <div className='border-t border-border px-4 py-3'>
            {error && (
                <div className="mb-3 p-3 bg-destructive/10 border border-destructive/20 text-destructive rounded-md flex items-center gap-2 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    {error}
                </div>
            )}
            
            <div className='flex flex-wrap gap-2 mb-3'>
              {QUICK_ACTIONS.map((action, index) => (
                <Button
                  key={index}
                  variant='outline'
                  size='sm'
                  className='text-xs bg-transparent border-border text-muted-foreground hover:text-foreground hover:bg-secondary cursor-pointer'
                  onClick={() => handleQuickAction(action.prompt)}
                  disabled={isAgentTyping}
                >
                  <HelpCircle className='w-3 h-3 mr-1' />
                  {action.label}
                </Button>
              ))}
            </div>

            {/* User Input */}
            <div className='flex gap-2'>
              <Textarea
                ref={inputRef}
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder='Type your question or opinion as Presiding Judge...'
                className='min-h-[60px] max-h-[120px] bg-secondary border-border text-foreground placeholder:text-muted-foreground resize-none'
                disabled={isAgentTyping}
              />
              <div className='flex flex-col gap-2'>
                <Button
                  onClick={() => handleUserSubmit()}
                  disabled={!userInput.trim() || isAgentTyping}
                  className='bg-primary hover:bg-primary/90 text-primary-foreground h-full cursor-pointer'
                >
                  <Send className='w-4 h-4' />
                </Button>
              </div>
            </div>

            {/* Generate Opinion Button */}
            <div className='mt-3 flex justify-end'>
              <Button
                onClick={handleGenerateOpinion}
                disabled={messages.length < 3 || isAgentTyping || isGeneratingOpinion}
                className='bg-accent hover:bg-accent/90 text-accent-foreground cursor-pointer'
              >
                {isGeneratingOpinion ? (
                  <>
                    <Loader2 className='w-4 h-4 mr-2 animate-spin' />
                    Generating Opinion...
                  </>
                ) : (
                  <>
                    <Gavel className='w-4 h-4 mr-2' />
                    Generate Legal Opinion
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
