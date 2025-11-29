'use client';

import type React from 'react';
import { usePathname } from 'next/navigation';
import { FileText, Users, Scale } from 'lucide-react';
import { cn } from '@/lib/utils';

export function StepProgress() {
  const pathname = usePathname();

  const steps = [
    { path: '/', label: 'Case Input', icon: FileText },
    { path: '/deliberation', label: 'Deliberation', icon: Users },
    { path: '/opinion', label: 'Legal Opinion', icon: Scale },
  ];

  const getCurrentStepIndex = () => {
    if (pathname === '/') return 0;
    if (pathname === '/deliberation') return 1;
    if (pathname === '/opinion') return 2;
    return 0;
  };

  const currentStep = getCurrentStepIndex();

  return (
    <div className='flex items-center justify-center gap-4 mb-8'>
      {steps.map((step, index) => (
        <div key={step.path} className='flex items-center'>
          {index > 0 && <div className='w-12 h-px bg-border mx-2' />}
          <StepIndicator
            label={step.label}
            icon={<step.icon className='w-4 h-4' />}
            active={index === currentStep}
            completed={index < currentStep}
          />
        </div>
      ))}
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
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors',
          active && 'bg-primary text-primary-foreground',
          completed && 'bg-accent text-accent-foreground',
          !active && !completed && 'bg-secondary text-muted-foreground',
        )}
      >
        {completed ? '✓' : icon}
      </div>
      <span
        className={cn(
          'text-sm transition-colors',
          active ? 'text-foreground font-medium' : 'text-muted-foreground',
        )}
      >
        {label}
      </span>
    </div>
  );
}
