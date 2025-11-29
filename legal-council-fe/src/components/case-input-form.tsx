'use client';

import type React from 'react';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, Upload, Sparkles } from 'lucide-react';

const EXAMPLE_CASES = [
  {
    title: 'Narcotics Case - 5 grams of Methamphetamine',
    description: 'First-time offender, claims personal use',
    facts:
      'Defendant found with 5 grams of methamphetamine (sabu-sabu), first-time offender, claims personal use. Defendant is a 28-year-old private employee with no prior criminal record. Evidence was found in pants pocket during a raid at a nightclub.',
  },
  {
    title: 'Corruption Case - Village Funds',
    description: 'Village head, misuse of IDR 500 million',
    facts:
      'Defendant as Village Head is charged with misappropriating Village Funds amounting to IDR 500,000,000 for personal gain. Defendant served for 4 years, funds were used for private home renovation and vehicle purchase. State losses have been calculated by BPKP (Financial and Development Supervisory Agency).',
  },
];

interface CaseInputFormProps {
  onSubmit: (facts: string) => void;
}

export function CaseInputForm({ onSubmit }: CaseInputFormProps) {
  const [facts, setFacts] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!facts.trim()) return;
    setIsLoading(true);
    await new Promise((r) => setTimeout(r, 500));
    onSubmit(facts);
  };

  const handleExampleClick = (exampleFacts: string) => {
    setFacts(exampleFacts);
  };

  return (
    <div className='space-y-6'>
      <Card className='bg-card border-border'>
        <CardHeader>
          <CardTitle className='flex items-center gap-2 text-foreground'>
            <FileText className='w-5 h-5 text-primary' />
            Enter Case Facts
          </CardTitle>
          <CardDescription className='text-muted-foreground'>
            Type a summary of the indictment or case facts to be deliberated by the AI Council
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className='space-y-4'>
            <Textarea
              placeholder='Example: Defendant found with 5g of methamphetamine, first-time offender, claims personal use...'
              value={facts}
              onChange={(e) => setFacts(e.target.value)}
              className='min-h-[200px] bg-secondary border-border text-foreground placeholder:text-muted-foreground resize-none'
            />

            <div className='flex items-center justify-between'>
              <div className='flex items-center gap-2 text-sm text-muted-foreground'>
                <Upload className='w-4 h-4' />
                <span>Or upload PDF document (coming soon)</span>
              </div>

              <Button
                type='submit'
                disabled={!facts.trim() || isLoading}
                className='bg-primary hover:bg-primary/90 text-primary-foreground'
              >
                <Sparkles className='w-4 h-4 mr-2' />
                {isLoading ? 'Processing...' : 'Start Deliberation'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className='space-y-3'>
        <h3 className='text-sm font-medium text-muted-foreground'>Example Cases</h3>
        <div className='grid md:grid-cols-2 gap-4'>
          {EXAMPLE_CASES.map((example, index) => (
            <Card
              key={index}
              className='bg-secondary border-border cursor-pointer hover:bg-secondary/80 transition-colors'
              onClick={() => handleExampleClick(example.facts)}
            >
              <CardContent className='p-4'>
                <h4 className='font-medium text-foreground mb-1'>{example.title}</h4>
                <p className='text-sm text-muted-foreground'>{example.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
