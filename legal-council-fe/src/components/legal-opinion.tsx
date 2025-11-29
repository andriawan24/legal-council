'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AgentAvatar } from './agent-avatar';
import { Scale, FileText, RotateCcw, Download, CheckCircle, AlertCircle } from 'lucide-react';
import { DeliberationMessage, LegalOpinionDraft, CouncilMemberRole } from '@/types/legal-council';

interface LegalOpinionProps {
  opinion: LegalOpinionDraft;
  messages: DeliberationMessage[];
  onReset: () => void;
}

export function LegalOpinion({ opinion, messages, onReset }: LegalOpinionProps) {
  
  // Helper to format sentence range
  const formatSentence = (range: { minimum: number; maximum: number; recommended: number }) => {
    if (!range) return 'N/A';
    return `${range.recommended} months (Range: ${range.minimum}-${range.maximum} months)`;
  };
  
  // Helper to extract arguments for a specific agent from the structured list
  const getArgumentsForAgent = (agentId: string) => {
    const args: string[] = [];
    
    // Check 'for_conviction'
    if (opinion.legal_arguments.for_conviction) {
      opinion.legal_arguments.for_conviction.forEach((arg) => {
        if (arg.source_agent === agentId) args.push(arg.argument);
      });
    }
    // Check 'for_leniency'
    if (opinion.legal_arguments.for_leniency) {
      opinion.legal_arguments.for_leniency.forEach((arg) => {
        if (arg.source_agent === agentId) args.push(arg.argument);
      });
    }
    // Check 'for_severity'
    if (opinion.legal_arguments.for_severity) {
      opinion.legal_arguments.for_severity.forEach((arg) => {
        if (arg.source_agent === agentId) args.push(arg.argument);
      });
    }
    
    return args;
  };

  const strictArgs = getArgumentsForAgent('strict');
  const humanistArgs = getArgumentsForAgent('humanist');
  const historianArgs = getArgumentsForAgent('historian');

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
          {/* Summary / Disclaimer */}
          <div>
            <h3 className='text-sm font-medium text-muted-foreground mb-2'>Reasoning</h3>
            <p className='text-foreground italic'>{opinion.verdict_recommendation.reasoning}</p>
          </div>

          {/* Verdict Recommendation */}
          <div className='grid md:grid-cols-2 gap-4'>
            <div className='bg-secondary rounded-lg p-4'>
              <div className='flex items-center gap-2 mb-2'>
                <CheckCircle className='w-4 h-4 text-accent' />
                <h3 className='text-sm font-medium text-foreground'>Recommended Verdict</h3>
              </div>
              <p className='text-foreground font-medium capitalize'>{opinion.recommended_verdict || opinion.verdict_recommendation.decision}</p>
              <p className='text-xs text-muted-foreground mt-1'>Confidence: {opinion.verdict_recommendation.confidence}</p>
            </div>
            <div className='bg-secondary rounded-lg p-4'>
              <div className='flex items-center gap-2 mb-2'>
                <AlertCircle className='w-4 h-4 text-primary' />
                <h3 className='text-sm font-medium text-foreground'>Sentence Recommendation</h3>
              </div>
              <p className='text-foreground font-medium'>{formatSentence(opinion.sentence_recommendation.imprisonment_months)}</p>
              {opinion.sentence_recommendation?.fine_idr && (
                <p className='text-xs text-muted-foreground mt-1'>
                  Fine: {opinion.sentence_recommendation.fine_idr.recommended.toLocaleString()} (Min: {opinion.sentence_recommendation.fine_idr.minimum.toLocaleString()})
                </p>
              )}
            </div>
          </div>

          {/* Key Arguments */}
          <div>
            <h3 className='text-sm font-medium text-muted-foreground mb-3'>
              Key Arguments from Each Perspective
            </h3>
            <div className='space-y-3'>
              {strictArgs.length > 0 && (
                <div className='bg-secondary rounded-lg p-3'>
                  <span className='text-xs font-medium text-primary'>Strict Constructionist</span>
                  <ul className='list-disc pl-4 mt-1'>
                    {strictArgs.map((arg, i) => (
                      <li key={i} className='text-sm text-foreground'>{arg}</li>
                    ))}
                  </ul>
                </div>
              )}
              {humanistArgs.length > 0 && (
                <div className='bg-secondary rounded-lg p-3'>
                  <span className='text-xs font-medium text-green-600'>Rehabilitative</span>
                   <ul className='list-disc pl-4 mt-1'>
                    {humanistArgs.map((arg, i) => (
                      <li key={i} className='text-sm text-foreground'>{arg}</li>
                    ))}
                  </ul>
                </div>
              )}
               {historianArgs.length > 0 && (
                <div className='bg-secondary rounded-lg p-3'>
                  <span className='text-xs font-medium text-blue-600'>Jurisprudence</span>
                   <ul className='list-disc pl-4 mt-1'>
                    {historianArgs.map((arg, i) => (
                      <li key={i} className='text-sm text-foreground'>{arg}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Relevant Precedents */}
          <div>
            <h3 className='text-sm font-medium text-muted-foreground mb-2'>
              Relevant Jurisprudence
            </h3>
            <div className='flex flex-wrap gap-2'>
              {opinion.cited_precedents && opinion.cited_precedents.map((precedent, index) => (
                <span
                  key={index}
                  className='text-xs px-3 py-1.5 bg-primary/20 text-primary rounded-full'
                  title={`${precedent.verdict_summary}`}
                >
                  {precedent.case_number || precedent.verdict_number}
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
               {/* Use sender as agent ID, explicitly casting if needed */}
              <AgentAvatar agent={message.sender as CouncilMemberRole | 'user' | 'system'} size='sm' />
              <div className='flex-1'>
                <span className='font-medium text-sm text-foreground'>{message.sender_name}</span>
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
