'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AgentAvatar } from './agent-avatar';
import { Scale, FileText, RotateCcw, Download, CheckCircle, AlertCircle } from 'lucide-react';
import { AgentMessage, LegalOpinionData } from '@/types';

interface LegalOpinionProps {
  opinion: LegalOpinionData;
  messages: AgentMessage[];
  onReset: () => void;
}

export function LegalOpinion({ opinion, messages, onReset }: LegalOpinionProps) {
  return (
    <div className='space-y-6'>
      {/* Main Opinion Card */}
      <Card className='bg-card border-border border-l-4 border-l-primary'>
        <CardHeader>
          <CardTitle className='flex items-center gap-2 text-foreground'>
            <Scale className='w-5 h-5 text-primary' />
            Draft Legal Opinion
          </CardTitle>
        </CardHeader>
        <CardContent className='space-y-6'>
          {/* Summary */}
          <div>
            <h3 className='text-sm font-medium text-muted-foreground mb-2'>Summary</h3>
            <p className='text-foreground'>{opinion.summary}</p>
          </div>

          {/* Verdict Recommendation */}
          <div className='grid md:grid-cols-2 gap-4'>
            <div className='bg-secondary rounded-lg p-4'>
              <div className='flex items-center gap-2 mb-2'>
                <CheckCircle className='w-4 h-4 text-accent' />
                <h3 className='text-sm font-medium text-foreground'>Recommended Verdict</h3>
              </div>
              <p className='text-foreground font-medium'>{opinion.recommendedVerdict}</p>
            </div>
            <div className='bg-secondary rounded-lg p-4'>
              <div className='flex items-center gap-2 mb-2'>
                <AlertCircle className='w-4 h-4 text-primary' />
                <h3 className='text-sm font-medium text-foreground'>Sentence Range</h3>
              </div>
              <p className='text-foreground font-medium'>{opinion.sentenceRange}</p>
            </div>
          </div>

          {/* Key Arguments */}
          <div>
            <h3 className='text-sm font-medium text-muted-foreground mb-3'>
              Key Arguments from Each Perspective
            </h3>
            <div className='space-y-3'>
              {opinion.keyArguments.map((arg, index) => (
                <div key={index} className='bg-secondary rounded-lg p-3'>
                  <span className='text-xs font-medium text-primary'>{arg.perspective}</span>
                  <p className='text-sm text-foreground mt-1'>{arg.argument}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Relevant Precedents */}
          <div>
            <h3 className='text-sm font-medium text-muted-foreground mb-2'>
              Relevant Jurisprudence
            </h3>
            <div className='flex flex-wrap gap-2'>
              {opinion.relevantPrecedents.map((precedent, index) => (
                <span
                  key={index}
                  className='text-xs px-3 py-1.5 bg-primary/20 text-primary rounded-full'
                >
                  {precedent}
                </span>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Debate Log */}
      <Card className='bg-card border-border'>
        <CardHeader>
          <CardTitle className='flex items-center gap-2 text-foreground text-base'>
            <FileText className='w-4 h-4 text-primary' />
            Deliberation Log
          </CardTitle>
        </CardHeader>
        <CardContent className='space-y-4 max-h-[400px] overflow-y-auto'>
          {messages.map((message) => (
            <div key={message.id} className='flex gap-3'>
              <AgentAvatar agent={message.agent} size='sm' />
              <div className='flex-1'>
                <span className='font-medium text-sm text-foreground'>{message.agentName}</span>
                <p className='text-sm text-muted-foreground mt-1 line-clamp-3'>{message.content}</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className='flex justify-center gap-4'>
        <Button
          variant='outline'
          onClick={onReset}
          className='border-border text-foreground hover:bg-secondary bg-transparent'
        >
          <RotateCcw className='w-4 h-4 mr-2' />
          New Case
        </Button>
        <Button className='bg-primary hover:bg-primary/90 text-primary-foreground'>
          <Download className='w-4 h-4 mr-2' />
          Download PDF
        </Button>
      </div>
    </div>
  );
}
