'use client';

import { createContext, useContext, useState, ReactNode } from 'react';
import { DeliberationMessage, LegalOpinionDraft } from '@/types/legal-council';

interface LegalCouncilContextType {
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  caseFacts: string;
  setCaseFacts: (facts: string) => void;
  messages: DeliberationMessage[];
  setMessages: (messages: DeliberationMessage[]) => void;
  opinion: LegalOpinionDraft | null;
  setOpinion: (opinion: LegalOpinionDraft | null) => void;
  reset: () => void;
}

const LegalCouncilContext = createContext<LegalCouncilContextType | undefined>(undefined);

export function LegalCouncilProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [caseFacts, setCaseFacts] = useState('');
  const [messages, setMessages] = useState<DeliberationMessage[]>([]);
  const [opinion, setOpinion] = useState<LegalOpinionDraft | null>(null);

  const reset = () => {
    setSessionId(null);
    setCaseFacts('');
    setMessages([]);
    setOpinion(null);
  };

  return (
    <LegalCouncilContext.Provider
      value={{
        sessionId,
        setSessionId,
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
