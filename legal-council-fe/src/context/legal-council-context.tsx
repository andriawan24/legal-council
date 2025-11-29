'use client';

import { createContext, useContext, useState, ReactNode } from 'react';
import { AgentMessage, LegalOpinionData } from '@/types';

interface LegalCouncilContextType {
  caseFacts: string;
  setCaseFacts: (facts: string) => void;
  messages: AgentMessage[];
  setMessages: (messages: AgentMessage[]) => void;
  opinion: LegalOpinionData | null;
  setOpinion: (opinion: LegalOpinionData | null) => void;
  reset: () => void;
}

const LegalCouncilContext = createContext<LegalCouncilContextType | undefined>(undefined);

export function LegalCouncilProvider({ children }: { children: ReactNode }) {
  const [caseFacts, setCaseFacts] = useState('');
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [opinion, setOpinion] = useState<LegalOpinionData | null>(null);

  const reset = () => {
    setCaseFacts('');
    setMessages([]);
    setOpinion(null);
  };

  return (
    <LegalCouncilContext.Provider
      value={{
        caseFacts,
        setCaseFacts,
        messages,
        setMessages,
        opinion,
        setOpinion,
        reset,
      }}
    >
      {children}
    </LegalCouncilContext.Provider>
  );
}

export function useLegalCouncil() {
  const context = useContext(LegalCouncilContext);
  if (context === undefined) {
    throw new Error('useLegalCouncil must be used within a LegalCouncilProvider');
  }
  return context;
}
