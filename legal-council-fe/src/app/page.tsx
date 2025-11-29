'use client';

import { useRouter } from 'next/navigation';
import { CaseInputForm } from '@/components/case-input-form';
import { useLegalCouncil } from '@/context/legal-council-context';

export default function Home() {
  const router = useRouter();
  const { setCaseFacts, reset } = useLegalCouncil();

  const handleStartDeliberation = (facts: string) => {
    reset();
    setCaseFacts(facts);
    router.push('/deliberation');
  };

  return <CaseInputForm onSubmit={handleStartDeliberation} />;
}
