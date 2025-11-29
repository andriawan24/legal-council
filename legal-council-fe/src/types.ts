export type AgentMessage = {
  id: string;
  agent: 'strict' | 'humanist' | 'historian' | 'user' | 'system';
  agentName: string;
  content: string;
  citations?: string[];
};

export type LegalOpinionData = {
  summary: string;
  recommendedVerdict: string;
  sentenceRange: string;
  keyArguments: { perspective: string; argument: string }[];
  relevantPrecedents: string[];
};
