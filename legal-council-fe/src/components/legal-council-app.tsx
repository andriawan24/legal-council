'use client';

import type React from 'react';

import { useState } from 'react';
import { CaseInputForm } from './case-input-form';
import { CouncilDebate } from './council-debate';
import { LegalOpinion } from './legal-opinion';
import { Header } from './header';
import { Scale, Users, FileText } from 'lucide-react';

export type AgentMessage = {
  id: string;
  agent: 'strict' | 'humanist' | 'historian' | 'user' | 'system';
  agentName: string;
  content: string;
  citations?: string[];
};

export type LegalOpinionData = {
  summary: string;
  recommendedVerdict: string;
  sentenceRange: string;
  keyArguments: { perspective: string; argument: string }[];
  relevantPrecedents: string[];
};

export type DeliberationState = 'input' | 'deliberating' | 'complete';

export function LegalCouncilApp() {
  const [state, setState] = useState<DeliberationState>('input');
  const [caseFacts, setCaseFacts] = useState('');
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [opinion, setOpinion] = useState<LegalOpinionData | null>(null);

  const handleStartDeliberation = (facts: string) => {
    setCaseFacts(facts);
    setState('deliberating');
    setMessages([]);
    setOpinion(null);
  };

  const handleDeliberationComplete = (
    finalMessages: AgentMessage[],
    finalOpinion: LegalOpinionData,
  ) => {
    setMessages(finalMessages);
    setOpinion(finalOpinion);
    setState('complete');
  };

  const handleReset = () => {
    setState('input');
    setCaseFacts('');
    setMessages([]);
    setOpinion(null);
  };

  return (
    <div className='min-h-screen bg-background'>
      <Header />

      <main className='container mx-auto px-4 py-8 max-w-5xl'>
        {/* Steps indicator */}
        <div className='flex items-center justify-center gap-4 mb-8'>
          <StepIndicator
            label='Case Input'
            icon={<FileText className='w-4 h-4' />}
            active={state === 'input'}
            completed={state !== 'input'}
          />
          <div className='w-12 h-px bg-border' />
          <StepIndicator
            label='Deliberation'
            icon={<Users className='w-4 h-4' />}
            active={state === 'deliberating'}
            completed={state === 'complete'}
          />
          <div className='w-12 h-px bg-border' />
          <StepIndicator
            label='Legal Opinion'
            icon={<Scale className='w-4 h-4' />}
            active={state === 'complete'}
            completed={false}
          />
        </div>

        {state === 'input' && <CaseInputForm onSubmit={handleStartDeliberation} />}

        {state === 'deliberating' && (
          <CouncilDebate caseFacts={caseFacts} onComplete={handleDeliberationComplete} />
        )}

        {state === 'complete' && opinion && (
          <LegalOpinion opinion={opinion} messages={messages} onReset={handleReset} />
        )}
      </main>
    </div>
  );
}

function StepIndicator({
  label,
  icon,
  active,
  completed,
}: {
  label: string;
  icon: React.ReactNode;
  active: boolean;
  completed: boolean;
}) {
  return (
    <div className='flex items-center gap-2'>
      <div
        className={`
          w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
          transition-colors
          ${active ? 'bg-primary text-primary-foreground' : ''}
          ${completed ? 'bg-accent text-accent-foreground' : ''}
          ${!active && !completed ? 'bg-secondary text-muted-foreground' : ''}
        `}
      >
        {completed ? '✓' : icon}
      </div>
      <span
        className={`text-sm ${active ? 'text-foreground font-medium' : 'text-muted-foreground'}`}
      >
        {label}
      </span>
    </div>
  );
}
