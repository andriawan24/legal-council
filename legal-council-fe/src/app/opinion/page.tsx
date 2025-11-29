'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { LegalOpinion } from '@/components/legal-opinion';
import { useLegalCouncil } from '@/context/legal-council-context';

export default function OpinionPage() {
  const router = useRouter();
  const { opinion, messages, reset } = useLegalCouncil();

  useEffect(() => {
    if (!opinion) {
      router.replace('/');
    }
  }, [opinion, router]);

  const handleReset = () => {
    reset();
    router.push('/');
  };

  if (!opinion) return null;

  return <LegalOpinion opinion={opinion} messages={messages} onReset={handleReset} />;
}
