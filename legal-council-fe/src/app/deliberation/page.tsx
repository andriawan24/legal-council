'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { CouncilDebate } from '@/components/council-debate';
import { useLegalCouncil } from '@/context/legal-council-context';
import type { AgentMessage, LegalOpinionData } from '@/types';

export default function DeliberationPage() {
  const router = useRouter();
  const { caseFacts, setMessages, setOpinion } = useLegalCouncil();

  useEffect(() => {
    if (!caseFacts) {
      router.replace('/');
    }
  }, [caseFacts, router]);

  const handleDeliberationComplete = (
    finalMessages: AgentMessage[],
    finalOpinion: LegalOpinionData,
  ) => {
    setMessages(finalMessages);
    setOpinion(finalOpinion);
    router.push('/opinion');
  };

  if (!caseFacts) return null;

  return <CouncilDebate caseFacts={caseFacts} onComplete={handleDeliberationComplete} />;
}
