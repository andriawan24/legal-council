'use client';

import { useEffect } from 'react';
import { CaseInputForm } from '@/components/case-input-form';
import { useLegalCouncil } from '@/context/legal-council-context';

export default function Home() {
  const { reset } = useLegalCouncil();

  // Reset state when visiting home page to clear previous sessions
  useEffect(() => {
    reset();
  }, [reset]);

  // CaseInputForm handles the submission, state updates, and navigation
  return <CaseInputForm />;
}
