import {
  CaseRecord,
  LegalOpinionDraft,
  DeliberationMessage,
  CouncilMemberRole,
  CaseInput,
} from './legal-council';

// Request Types
export interface CreateSessionRequest {
  input_type: 'text_summary' | 'structured_form' | 'pdf_upload';
  case_summary: string;
  case_type?: 'narcotics' | 'corruption' | 'general_criminal' | 'other';
  structured_data?: Record<string, unknown>;
}

export type MessageIntent =
  | 'present_case'
  | 'ask_opinion'
  | 'ask_precedent'
  | 'challenge_argument'
  | 'request_clarification'
  | 'provide_analysis'
  | 'cite_precedent'
  | 'summarize';

export type AgentId = CouncilMemberRole | 'all';

export interface SendMessageRequest {
  content: string;
  intent?: MessageIntent;
  target_agent?: AgentId;
}

export interface SearchCasesRequest {
  query: string;
  semantic_search?: boolean;
  filters?: {
    case_type?: string;
    substance_type?: string;
    min_weight?: number;
    max_weight?: number;
  };
  limit?: number;
  offset?: number;
}

// Response Types
export interface CreateSessionResponse {
  session_id: string;
  parsed_case: string | null; // using any for now as ParsedCase structure might vary from CaseRecord
  similar_cases: CaseRecord[];
  initial_message: DeliberationMessage;
  created_at: string;
}

// Full deliberation session
export interface DeliberationSessionResponse {
  id: string;
  user_id: string | null;
  status: string;
  case_input: CaseInput;
  similar_cases: CaseRecord[];
  messages: DeliberationMessage[];
  legal_opinion: LegalOpinionDraft | null;
  created_at: string;
  updated_at: string;
  concluded_at: string | null;
}

// Response wrapping the session
export interface SessionResponse {
  session: DeliberationSessionResponse;
}

export interface PaginationInfo {
  total: number;
  page: number;
  limit: number;
}

export interface ListSessionsResponse {
  sessions: DeliberationSessionResponse[];
  pagination: PaginationInfo;
}

export interface SendMessageResponse {
  user_message: DeliberationMessage;
  agent_responses: DeliberationMessage[];
}

export interface GetMessagesResponse {
  messages: DeliberationMessage[];
}

export interface GenerateOpinionResponse {
  opinion: LegalOpinionDraft;
  session_status: 'concluded';
}

export interface SearchCasesResponse {
  cases: CaseRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface CaseResponse {
  case: CaseRecord;
}

export interface CaseStatisticsResponse {
  total_cases: number;
  by_type: Record<string, number>;
  by_verdict: Record<string, number>;
  avg_sentence_months: number;
}

// Stream Types
export type StreamChunk =
  | { type: 'user_message'; id: string; content: string }
  | { type: 'agent_start'; agent_id: CouncilMemberRole; agent_name: string }
  | { type: 'agent_chunk'; agent_id: CouncilMemberRole; content: string }
  | {
      type: 'agent_complete';
      agent_id: CouncilMemberRole;
      message_id: string;
      citations?: { cases: string[]; laws: string[] };
    }
  | { type: 'done' };
