'use client';

import type React from 'react';

import { useState, useRef, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { AgentAvatar } from './agent-avatar';
import { Loader2, Send, Gavel, HelpCircle } from 'lucide-react';
import type { AgentMessage, LegalOpinionData } from '@/types';
import { MessageBubble } from './message-bubble';

interface CouncilDebateProps {
  caseFacts: string;
  onComplete: (messages: AgentMessage[], opinion: LegalOpinionData) => void;
}

const AGENTS = {
  strict: {
    name: 'Judge A - Strict Constructionist',
    shortName: 'Judge A',
    role: 'Strict Constructionist',
  },
  humanist: {
    name: 'Judge B - Rehabilitative Approach',
    shortName: 'Judge B',
    role: 'Humanist',
  },
  historian: {
    name: 'Judge C - Jurisprudence Expert',
    shortName: 'Judge C',
    role: 'Historian',
  },
  user: {
    name: 'You (Presiding Judge)',
    shortName: 'You',
    role: 'Presiding Judge',
  },
  system: {
    name: 'System',
    shortName: 'System',
    role: 'System',
  },
};

const QUICK_ACTIONS = [
  { label: "Ask Judge A's opinion", prompt: 'Judge A, what is your opinion on this case?' },
  {
    label: "Ask Judge B's opinion",
    prompt: 'Judge B, from a rehabilitation perspective, what is your view?',
  },
  {
    label: 'Ask about precedents',
    prompt: 'Judge C, are there any relevant precedents or jurisprudence for this case?',
  },
  { label: 'Request clarification', prompt: 'Could you elaborate more on the legal basis?' },
];

const getAgentResponse = (
  agent: 'strict' | 'humanist' | 'historian',
  context: { caseFacts: string; lastUserMessage: string; messageHistory: AgentMessage[] },
): { content: string; citations: string[] } => {
  const { caseFacts, lastUserMessage, messageHistory } = context;
  const isNarcotics =
    caseFacts.toLowerCase().includes('sabu') ||
    caseFacts.toLowerCase().includes('methamphetamine') ||
    caseFacts.toLowerCase().includes('narcotics');
  const isFirstResponse = !messageHistory.some((m) => m.agent === agent);
  const isDirectlyAsked = lastUserMessage
    .toLowerCase()
    .includes(AGENTS[agent].shortName.toLowerCase());

  const askingAboutPrecedent =
    lastUserMessage.toLowerCase().includes('precedent') ||
    lastUserMessage.toLowerCase().includes('jurisprudence');
  const askingAboutRehab =
    lastUserMessage.toLowerCase().includes('rehabilit') ||
    lastUserMessage.toLowerCase().includes('rehab');
  const askingAboutLaw =
    lastUserMessage.toLowerCase().includes('legal basis') ||
    lastUserMessage.toLowerCase().includes('article');

  if (isNarcotics) {
    const responses: Record<
      'strict' | 'humanist' | 'historian',
      {
        initial: { content: string; citations: string[] };
        followUp: { content: string; citations: string[] };
        onLaw?: { content: string; citations: string[] };
        onRehab?: { content: string; citations: string[] };
        onPrecedent?: { content: string; citations: string[] };
      }
    > = {
      strict: {
        initial: {
          content: `Thank you, Your Honor.\n\nBased on Narcotics Law No. 35 of 2009 Article 112 paragraph (1), possession of Category I narcotics weighing 5 grams constitutes a criminal offense punishable by a minimum of 4 years imprisonment.\n\nThe elements of the crime are fulfilled: there is evidence, there is possession, and the type of narcotics falls under Category I. The claim of "personal use" does not negate the element of illegal possession.`,
          citations: ['Law No. 35/2009 Article 112 paragraph (1)'],
        },
        followUp: {
          content: `Your Honor, I maintain my position based on textual interpretation of the law. Article 112 does not distinguish between dealers and users in terms of possession.\n\nAlthough a rehabilitative approach is possible, it does not eliminate criminal liability. The defendant must still undergo legal proceedings according to the provisions.`,
          citations: ['Law No. 35/2009', 'Criminal Procedure Code Article 197'],
        },
        onLaw: {
          content: `Yes, Your Honor. The main legal bases are:\n\n1. **Article 112 paragraph (1) Law No. 35/2009**: Anyone who possesses, stores, controls Category I narcotics is punishable by imprisonment of at least 4 years and at most 12 years.\n\n2. **Article 127 paragraph (1)**: For drug abusers, imprisonment of at most 4 years.\n\nThe key is the qualification of the defendant: whether as a possessor (Article 112) or abuser (Article 127).`,
          citations: ['Law No. 35/2009 Article 112', 'Law No. 35/2009 Article 127'],
        },
      },
      humanist: {
        initial: {
          content: `Thank you, Your Honor.\n\nI would like to highlight Supreme Court Circular (SEMA) No. 4 of 2010 which provides guidelines that narcotics addicts can be placed in rehabilitation facilities.\n\nThe defendant is a first-time offender with evidence weighing 5 grams - still within the category that can be considered for rehabilitation based on Government Regulation No. 25/2011. The purpose of punishment is not merely punitive, but also rehabilitative.`,
          citations: ['SEMA No. 4/2010', 'Government Regulation No. 25/2011'],
        },
        followUp: {
          content: `Your Honor, research shows that rehabilitation success rates reach 60% in preventing recidivism, compared to only 20% for imprisonment.\n\nConsidering the defendant claims personal use and there is no evidence of involvement in distribution, a rehabilitative approach aligns better with modern sentencing objectives.`,
          citations: ['SEMA No. 4/2010', 'Law No. 12/1995 on Corrections'],
        },
        onRehab: {
          content: `Exactly, Your Honor. Regarding rehabilitation:\n\n1. **SEMA No. 4/2010** allows judges to place defendants in rehabilitation if proven to be addicts.\n\n2. Requirements: evidence weight according to the table (methamphetamine maximum 1 gram for pure, or 5 grams for impure), medical certificate from a doctor, and no involvement in distribution.\n\n3. Designated rehabilitation facilities are available in every province.\n\nWith 5 grams weight and first-time offender status, the defendant meets the criteria for consideration.`,
          citations: [
            'SEMA No. 4/2010',
            'Government Regulation No. 25/2011',
            'Ministry of Health Regulation No. 50/2015',
          ],
        },
      },
      historian: {
        initial: {
          content: `Thank you, Your Honor.\n\nI found a highly relevant precedent:\n\n**Supreme Court Decision No. 2051K/Pid.Sus/2013**\n- Facts: Defendant caught with 4.8 grams of methamphetamine, first-time offender, claimed personal use\n- Verdict: 2 years imprisonment + 6 months rehabilitation\n- Ratio decidendi: Judge considered rehabilitation intent and first-time offender status\n\nThis decision can serve as a reference for our case.`,
          citations: ['Supreme Court No. 2051K/Pid.Sus/2013'],
        },
        followUp: {
          content: `Additionally, Your Honor, there is also **Supreme Court Decision No. 567K/Pid.Sus/2015** with similar weight (5.2 grams), but the defendant had prior criminal history and was sentenced to 5 years without rehabilitation.\n\nKey difference: first-time offender status. This is consistent with Supreme Court jurisprudence that gives special consideration to first-time offenders.`,
          citations: [
            'Supreme Court No. 567K/Pid.Sus/2015',
            'Supreme Court No. 1071K/Pid.Sus/2012',
          ],
        },
        onPrecedent: {
          content: `Yes, Your Honor. Let me summarize the relevant jurisprudence:\n\n| Decision No. | Evidence Weight | Status | Verdict |\n|-------------|----------|--------|--------|\n| 2051K/2013 | 4.8g | First-time | 2 yrs + rehab |\n| 567K/2015 | 5.2g | Recidivist | 5 years |\n| 1071K/2012 | 3.5g | First-time | 18 mos + rehab |\n\nPattern observed: first-time offenders with weight < 5 grams tend to receive verdicts with rehabilitation components. Our defendant is right at the threshold.`,
          citations: ['Supreme Court Jurisprudence 2012-2015'],
        },
      },
    };

    const agentData = responses[agent];

    if (isFirstResponse || isDirectlyAsked) {
      return agentData.initial;
    }
    if (askingAboutLaw && agent === 'strict' && agentData.onLaw) {
      return agentData.onLaw;
    }
    if (askingAboutRehab && agent === 'humanist' && agentData.onRehab) {
      return agentData.onRehab;
    }
    if (askingAboutPrecedent && agent === 'historian' && agentData.onPrecedent) {
      return agentData.onPrecedent;
    }
    return agentData.followUp;
  }

  // Default corruption case responses
  const corruptionResponses: Record<
    'strict' | 'humanist' | 'historian',
    {
      initial: { content: string; citations: string[] };
      followUp: { content: string; citations: string[] };
    }
  > = {
    strict: {
      initial: {
        content: `Thank you, Your Honor.\n\nBased on Anti-Corruption Law No. 31 of 1999 jo. Law No. 20 of 2001, the defendant's actions fulfill the elements of corruption as stipulated in Article 2 or Article 3.\n\nState losses amounting to IDR 500 million have been calculated by BPKP. The defendant as Village Head is a state official who must uphold public trust.`,
        citations: ['Law No. 31/1999', 'Law No. 20/2001'],
      },
      followUp: {
        content: `Your Honor, from a strict construction perspective, the elements of "unlawful act" and "self-enrichment" are fulfilled. The use of funds for private home renovation and vehicle purchase clearly demonstrates criminal intent (mens rea).\n\nThere are no justifiable or excusable grounds that can be accepted in this context.`,
        citations: ['Law No. 31/1999 Article 2', 'Law No. 31/1999 Article 3'],
      },
    },
    humanist: {
      initial: {
        content: `Thank you, Your Honor.\n\nWithout diminishing the seriousness of corruption crimes, I would like to consider mitigating factors:\n\n1. Was the defendant cooperative during investigation?\n2. Has there been any restitution of state losses?\n3. What were the socio-economic conditions of the village under leadership?\n\nRestorative justice approaches in corruption cases are developing with a focus on recovering state losses.`,
        citations: ['SEMA No. 1/2017', 'Supreme Court Regulation No. 1/2020'],
      },
      followUp: {
        content: `Your Honor, if the defendant is willing to fully restore state losses and shows remorse, this can be considered in determining the severity of punishment according to Article 4 of the Anti-Corruption Law.\n\nHowever, I agree that punishment must still be imposed for deterrent effect.`,
        citations: ['Law No. 20/2001 Article 4'],
      },
    },
    historian: {
      initial: {
        content: `Thank you, Your Honor.\n\nBased on jurisprudence, for village fund corruption with losses of IDR 500 million:\n\n**Supreme Court Decision No. 1261K/Pid.Sus/2015**\n- Losses: IDR 450 million\n- Verdict: 4 years imprisonment + IDR 200 million fine + restitution\n\nJurisprudence trends show proportionality between the amount of losses and imprisonment.`,
        citations: ['Supreme Court No. 1261K/Pid.Sus/2015'],
      },
      followUp: {
        content: `Additionally, Your Honor:\n\n| Loss Range | Average Sentence |\n|-----------------|------------------|\n| < 100 million | 1-3 years |\n| 100-500 million | 3-5 years |\n| 500 million - 1 B | 5-8 years |\n| > 1 Billion | 8-15 years |\n\nOur case (IDR 500 million) is at the upper boundary of the second category, so a range of 4-6 years is reasonable based on jurisprudence.`,
        citations: ['Supreme Court Jurisprudence 2015-2023'],
      },
    },
  };

  const agentData = corruptionResponses[agent];
  if (isFirstResponse || isDirectlyAsked) {
    return agentData.initial;
  }
  return agentData.followUp;
};

const getDummyOpinion = (caseFacts: string): LegalOpinionData => {
  const isNarcotics =
    caseFacts.toLowerCase().includes('sabu') ||
    caseFacts.toLowerCase().includes('methamphetamine') ||
    caseFacts.toLowerCase().includes('narcotics');

  if (isNarcotics) {
    return {
      summary:
        "Based on the Panel of Judges' deliberation considering arguments from all three perspectives, this case requires a balance between law enforcement and rehabilitative approach. The defendant as a first-time offender with claims of personal use deserves special consideration based on SEMA No. 4/2010 and relevant Supreme Court jurisprudence.",
      recommendedVerdict:
        'Guilty of violating Article 112 paragraph (1) Law No. 35/2009, with recommendation for rehabilitation',
      sentenceRange:
        '2-3 years imprisonment with 6 months rehabilitation period at designated facility',
      keyArguments: [
        {
          perspective: 'Strict Constructionist',
          argument:
            'Elements of crime are fulfilled based on Article 112 Narcotics Law. Possession is an undeniable fact.',
        },
        {
          perspective: 'Rehabilitative Approach',
          argument:
            'First-time offender status and claim of personal use support application of SEMA No. 4/2010 on rehabilitation.',
        },
        {
          perspective: 'Jurisprudence Expert',
          argument:
            'Precedent Supreme Court No. 2051K/Pid.Sus/2013 with similar facts resulted in 2 years + rehabilitation verdict.',
        },
      ],
      relevantPrecedents: [
        'Supreme Court No. 2051K/Pid.Sus/2013',
        'Supreme Court No. 1386K/Pid.Sus/2011',
        'SEMA No. 4/2010',
      ],
    };
  }

  return {
    summary:
      "Based on the Panel of Judges' deliberation, the defendant is proven to have committed corruption with state losses of IDR 500 million. Considering jurisprudence and proportionality principles, the sentence imposed must reflect the seriousness of the act while providing deterrent effect.",
    recommendedVerdict:
      'Guilty of committing corruption according to Article 2 or Article 3 of Anti-Corruption Law',
    sentenceRange: '4-5 years imprisonment + IDR 200 million fine + IDR 500 million restitution',
    keyArguments: [
      {
        perspective: 'Strict Constructionist',
        argument:
          'Elements of corruption are fulfilled: unlawful act, self-enrichment, causing state financial loss.',
      },
      {
        perspective: 'Rehabilitative Approach',
        argument: 'Obligation to restore state losses must be an integral part of the verdict.',
      },
      {
        perspective: 'Jurisprudence Expert',
        argument: 'Jurisprudence shows a range of 4-6 years for losses around IDR 500 million.',
      },
    ],
    relevantPrecedents: [
      'Supreme Court No. 1261K/Pid.Sus/2015',
      'Supreme Court No. 2623K/Pid.Sus/2018',
    ],
  };
};

export function CouncilDebate({ caseFacts, onComplete }: CouncilDebateProps) {
  const [messages, setMessages] = useState<AgentMessage[]>([
    {
      id: crypto.randomUUID(),
      agent: 'system',
      agentName: 'System',
      content: `Welcome to the Virtual Deliberation Room, Your Honor.\n\n**Case Facts:**\n${caseFacts}\n\nYou are the Presiding Judge leading this deliberation. Please begin by asking questions or requesting opinions from the panel members.`,
    },
  ]);
  const [userInput, setUserInput] = useState('');
  const [isAgentTyping, setIsAgentTyping] = useState(false);
  const [currentTypingAgent, setCurrentTypingAgent] = useState<
    'strict' | 'humanist' | 'historian' | null
  >(null);
  const [isGeneratingOpinion, setIsGeneratingOpinion] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getRespondingAgent = (userMessage: string): 'strict' | 'humanist' | 'historian' => {
    const msg = userMessage.toLowerCase();
    if (
      msg.includes('judge a') ||
      msg.includes('strict') ||
      msg.includes('article') ||
      msg.includes('legal basis')
    ) {
      return 'strict';
    }
    if (msg.includes('judge b') || msg.includes('rehabilit') || msg.includes('humanis')) {
      return 'humanist';
    }
    if (
      msg.includes('judge c') ||
      msg.includes('precedent') ||
      msg.includes('jurisprudence') ||
      msg.includes('decision')
    ) {
      return 'historian';
    }
    const agentMessages = messages.filter((m) =>
      ['strict', 'humanist', 'historian'].includes(m.agent),
    );
    const rotation: ('strict' | 'humanist' | 'historian')[] = ['strict', 'humanist', 'historian'];
    return rotation[agentMessages.length % 3];
  };

  const handleUserSubmit = async (text?: string) => {
    const messageText = text || userInput.trim();
    if (!messageText || isAgentTyping) return;

    const userMessage: AgentMessage = {
      id: crypto.randomUUID(),
      agent: 'user',
      agentName: 'You (Presiding Judge)',
      content: messageText,
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setUserInput('');

    const respondingAgent = getRespondingAgent(messageText);

    setIsAgentTyping(true);
    setCurrentTypingAgent(respondingAgent);

    await new Promise((resolve) => setTimeout(resolve, 1500));

    const response = getAgentResponse(respondingAgent, {
      caseFacts,
      lastUserMessage: messageText,
      messageHistory: updatedMessages,
    });

    const agentMessage: AgentMessage = {
      id: crypto.randomUUID(),
      agent: respondingAgent,
      agentName: AGENTS[respondingAgent].name,
      content: response.content,
      citations: response.citations,
    };

    setMessages([...updatedMessages, agentMessage]);
    setIsAgentTyping(false);
    setCurrentTypingAgent(null);

    inputRef.current?.focus();
  };

  const handleQuickAction = (prompt: string) => {
    handleUserSubmit(prompt);
  };

  const handleGenerateOpinion = async () => {
    setIsGeneratingOpinion(true);
    await new Promise((resolve) => setTimeout(resolve, 2000));
    const opinion = getDummyOpinion(caseFacts);
    onComplete(messages, opinion);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleUserSubmit();
    }
  };

  return (
    <div className='space-y-4'>
      <div className='flex items-center justify-center gap-6 py-3 px-4 bg-secondary rounded-lg'>
        <div className='flex items-center gap-2'>
          <AgentAvatar agent='user' size='sm' />
          <span className='text-xs text-foreground font-medium'>You (Presiding)</span>
        </div>
        <div className='w-px h-6 bg-border' />
        {(['strict', 'humanist', 'historian'] as const).map((agent) => (
          <div key={agent} className='flex items-center gap-2'>
            <AgentAvatar agent={agent} size='sm' />
            <span className='text-xs text-muted-foreground'>{AGENTS[agent].shortName}</span>
          </div>
        ))}
      </div>

      <Card className='bg-card border-border'>
        <CardContent className='p-0'>
          <div className='h-[450px] overflow-y-auto space-y-4'>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}

            {isAgentTyping && currentTypingAgent && (
              <div className='flex gap-3 mx-6'>
                <AgentAvatar agent={currentTypingAgent} size='md' />
                <div className='flex-1 max-w-[80%]'>
                  <span className='text-xs text-muted-foreground mb-1 block'>
                    {AGENTS[currentTypingAgent].name}
                  </span>
                  <div className='bg-secondary rounded-lg rounded-tl-none p-3'>
                    <div className='text-sm text-foreground'>
                      <span className='flex items-center gap-1 text-muted-foreground'>
                        <Loader2 className='w-3 h-3 animate-spin' />
                        Thinking...
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions */}
          <div className='border-t border-border px-4 py-3'>
            <div className='flex flex-wrap gap-2 mb-3'>
              {QUICK_ACTIONS.map((action, index) => (
                <Button
                  key={index}
                  variant='outline'
                  size='sm'
                  className='text-xs bg-transparent border-border text-muted-foreground hover:text-foreground hover:bg-secondary cursor-pointer'
                  onClick={() => handleQuickAction(action.prompt)}
                  disabled={isAgentTyping}
                >
                  <HelpCircle className='w-3 h-3 mr-1' />
                  {action.label}
                </Button>
              ))}
            </div>

            {/* User Input */}
            <div className='flex gap-2'>
              <Textarea
                ref={inputRef}
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder='Type your question or opinion as Presiding Judge...'
                className='min-h-[60px] max-h-[120px] bg-secondary border-border text-foreground placeholder:text-muted-foreground resize-none'
                disabled={isAgentTyping}
              />
              <div className='flex flex-col gap-2'>
                <Button
                  onClick={() => handleUserSubmit()}
                  disabled={!userInput.trim() || isAgentTyping}
                  className='bg-primary hover:bg-primary/90 text-primary-foreground h-full cursor-pointer'
                >
                  <Send className='w-4 h-4' />
                </Button>
              </div>
            </div>

            {/* Generate Opinion Button */}
            <div className='mt-3 flex justify-end'>
              <Button
                onClick={handleGenerateOpinion}
                disabled={messages.length < 3 || isAgentTyping || isGeneratingOpinion}
                className='bg-accent hover:bg-accent/90 text-accent-foreground cursor-pointer'
              >
                {isGeneratingOpinion ? (
                  <>
                    <Loader2 className='w-4 h-4 mr-2 animate-spin' />
                    Generating Opinion...
                  </>
                ) : (
                  <>
                    <Gavel className='w-4 h-4 mr-2' />
                    Generate Legal Opinion
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
