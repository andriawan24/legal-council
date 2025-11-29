'use client';

import type React from 'react';
import { LegalCouncilProvider } from '@/context/legal-council-context';
import { Header } from '@/components/header';
import { StepProgress } from '@/components/step-progress';

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <LegalCouncilProvider>
      <div className='min-h-screen bg-background'>
        <Header />
        <main className='container mx-auto px-4 py-8 max-w-5xl'>
          <StepProgress />
          {children}
        </main>
      </div>
    </LegalCouncilProvider>
  );
}
