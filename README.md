This project outlines the legal council's workflow, broken down into two main phases:

### Ingestion (Async) - `extraction-job/`
1.  **PDF Upload**: Users upload PDF documents.
2.  **GCS Trigger**: Uploads to Google Cloud Storage (GCS) trigger the next step.
3.  **Cloud Run Job**: A Cloud Run job processes the uploaded PDFs.
4.  **Vertex AI (Embed)**: Vertex AI embeds the document content into vectors.
5.  **Cloud SQL (Store Vector)**: The resulting vectors are stored in Cloud SQL.

### Deliberation (Real-time) - `api/`
1.  **User Input**: Users provide input for real-time deliberation.
2.  **FastAPI**: A FastAPI application handles user requests.
3.  **Cloud SQL (Vector Search)**: Performs vector searches in Cloud SQL.
4.  **Vertex AI (Debate Loop)**: Vertex AI runs a debate loop based on the search results.
5.  **Stream to User**: The deliberation results are streamed back to the user.


# Legal Council - Backend Product Requirements Document (PRD)

## 1. Product Overview

**Product Name:** Legal Council (Virtual Deliberation Room)

**Purpose:** AI-powered deliberation system that helps Indonesian judges achieve sentencing consistency by simulating a council of three AI judges with different legal perspectives, all grounded in actual Indonesian court verdict data.

**Target Users:** Judges, Legal Scholars, Law Students

---

## 2. System Architecture Overview

\`\`\`
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                       │
│  - Case Input Form                                              │
│  - Deliberation Chat Interface                                  │
│  - Legal Opinion Display                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API GATEWAY                              │
│  - Authentication                                               │
│  - Rate Limiting                                                │
│  - Request Validation                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND SERVICES                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Session   │  │    Case     │  │    AI Deliberation      │  │
│  │   Service   │  │   Search    │  │       Service           │  │
│  │             │  │   Service   │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  PostgreSQL │  │   Vector    │  │      Redis Cache        │  │
│  │  (Sessions, │  │   Database  │  │   (Session State,       │  │
│  │   Cases)    │  │  (Semantic  │  │    Rate Limiting)       │  │
│  │             │  │   Search)   │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
\`\`\`

---

## 3. Core Data Models

### 3.1 Case Record (from your dataset)

\`\`\`typescript
interface CaseRecord {
  id: string;                          // Unique identifier (generate if not in dataset)
  case_number: string;                 // e.g., "1234/Pid.Sus/2024/PN Jkt.Sel"

  court: {
    name: string;                      // e.g., "Pengadilan Negeri Jakarta Selatan"
    type: "district" | "high" | "supreme";
    location: string;
  };

  case_type: "narcotics" | "corruption" | "general_criminal" | "other";

  defendant: {
    name: string;
    age: number | null;
    gender: "male" | "female" | null;
    occupation: string | null;
    criminal_history: "first_offender" | "repeat_offender" | null;
  };

  indictment: {
    primary_charge: string;            // Article violated
    subsidiary_charge: string | null;
    prosecutor_demand: {
      imprisonment_months: number;
      fine_idr: number;
    };
  };

  // For narcotics cases
  narcotics_details: {
    substance_type: string;            // e.g., "methamphetamine", "cannabis"
    weight_grams: number;
    classification: "user" | "dealer" | "producer" | null;
    intent: "personal_use" | "distribution" | "unknown";
  } | null;

  // For corruption cases
  corruption_details: {
    state_loss_idr: number;
    position: string;
    institution: string;
    money_laundering: boolean;
    returned_amount_idr: number;
  } | null;

  legal_facts: {
    aggravating_factors: string[];
    mitigating_factors: string[];
    evidence_summary: string;
  };

  verdict: {
    decision: "guilty" | "not_guilty" | "acquitted";
    imprisonment_months: number;
    fine_idr: number;
    additional_penalties: string[];
    judge_reasoning: string;
  };

  legal_basis: {
    primary_law: string;               // e.g., "UU No. 35 Tahun 2009"
    articles_applied: string[];
    sema_references: string[];         // Supreme Court Circulars
    jurisprudence_cited: string[];     // Previous case numbers cited
  };

  metadata: {
    decision_date: string;             // ISO date
    panel_judges: string[];
    is_landmark_case: boolean;
    indexed_at: string;
  };
}
\`\`\`

### 3.2 Deliberation Session

\`\`\`typescript
interface DeliberationSession {
  id: string;                          // UUID
  user_id: string;                     // User who created the session
  status: "active" | "concluded" | "archived";

  case_input: {
    input_type: "text_summary" | "pdf_upload" | "structured_form";
    raw_input: string;                 // Original user input
    parsed_case: ParsedCaseInput;      // Structured extraction
  };

  similar_cases: SimilarCase[];        // Retrieved from database

  messages: DeliberationMessage[];

  legal_opinion: LegalOpinionDraft | null;

  created_at: string;
  updated_at: string;
  concluded_at: string | null;
}

interface ParsedCaseInput {
  case_type: "narcotics" | "corruption" | "other";
  summary: string;
  defendant_profile: {
    is_first_offender: boolean;
    age: number | null;
    occupation: string | null;
  };
  key_facts: string[];
  charges: string[];

  // Type-specific details
  narcotics?: {
    substance: string;
    weight_grams: number;
    intent: "personal_use" | "distribution" | "unknown";
  };
  corruption?: {
    state_loss_idr: number;
    position: string;
  };
}

interface SimilarCase {
  case_id: string;
  case_number: string;
  similarity_score: number;            // 0-1
  similarity_reason: string;
  verdict_summary: string;
  sentence_months: number;
}

interface DeliberationMessage {
  id: string;
  session_id: string;
  sender: MessageSender;
  content: string;
  intent: MessageIntent | null;
  cited_cases: string[];               // Case IDs referenced
  cited_laws: string[];                // Laws referenced
  timestamp: string;
}

type MessageSender =
  | { type: "user"; role: "presiding_judge" }
  | { type: "agent"; agent_id: "strict" | "humanist" | "historian" }
  | { type: "system" };

type MessageIntent =
  | "present_case"
  | "ask_opinion"
  | "ask_precedent"
  | "challenge_argument"
  | "request_clarification"
  | "provide_analysis"
  | "cite_precedent"
  | "summarize";
\`\`\`

### 3.3 Legal Opinion Draft

\`\`\`typescript
interface LegalOpinionDraft {
  session_id: string;
  generated_at: string;

  case_summary: string;

  verdict_recommendation: {
    decision: "guilty" | "not_guilty";
    confidence: "high" | "medium" | "low";
    reasoning: string;
  };

  sentence_recommendation: {
    imprisonment_months: {
      minimum: number;
      maximum: number;
      recommended: number;
    };
    fine_idr: {
      minimum: number;
      maximum: number;
      recommended: number;
    };
    additional_penalties: string[];
  };

  legal_arguments: {
    for_conviction: ArgumentPoint[];
    for_leniency: ArgumentPoint[];
    for_severity: ArgumentPoint[];
  };

  cited_precedents: CitedPrecedent[];

  applicable_laws: ApplicableLaw[];

  dissenting_views: string[];          // Minority opinions from agents
}

interface ArgumentPoint {
  argument: string;
  source_agent: "strict" | "humanist" | "historian";
  supporting_cases: string[];
  strength: "strong" | "moderate" | "weak";
}

interface CitedPrecedent {
  case_id: string;
  case_number: string;
  relevance: string;
  verdict_summary: string;
  how_it_applies: string;
}

interface ApplicableLaw {
  law_reference: string;               // e.g., "UU No. 35/2009 Pasal 127"
  description: string;
  how_it_applies: string;
}
\`\`\`

---

## 4. API Endpoints

### 4.1 Session Management

#### Create New Deliberation Session
\`\`\`
POST /api/v1/sessions

Request Body:
{
  "input_type": "text_summary" | "structured_form",
  "case_summary": string,
  "case_type"?: "narcotics" | "corruption" | "other",
  "structured_data"?: {
    // Optional structured input
    "defendant_first_offender": boolean,
    "substance_type"?: string,
    "weight_grams"?: number,
    "state_loss_idr"?: number
  }
}

Response:
{
  "session_id": string,
  "parsed_case": ParsedCaseInput,
  "similar_cases": SimilarCase[],
  "initial_message": DeliberationMessage  // System welcome message
}
\`\`\`

#### Get Session Details
\`\`\`
GET /api/v1/sessions/:sessionId

Response:
{
  "session": DeliberationSession
}
\`\`\`

#### List User Sessions
\`\`\`
GET /api/v1/sessions?status=active|concluded|all&page=1&limit=20

Response:
{
  "sessions": DeliberationSession[],
  "pagination": { "total": number, "page": number, "limit": number }
}
\`\`\`

#### Archive/Delete Session
\`\`\`
DELETE /api/v1/sessions/:sessionId
\`\`\`

---

### 4.2 Deliberation (Chat)

#### Send Message & Get Agent Response
\`\`\`
POST /api/v1/sessions/:sessionId/messages

Request Body:
{
  "content": string,
  "intent"?: MessageIntent,
  "target_agent"?: "strict" | "humanist" | "historian" | "all"
}

Response (Streaming SSE recommended):
{
  "user_message": DeliberationMessage,
  "agent_responses": DeliberationMessage[]  // 1-3 responses based on context
}
\`\`\`

#### Get Message History
\`\`\`
GET /api/v1/sessions/:sessionId/messages?limit=50&before=:messageId

Response:
{
  "messages": DeliberationMessage[]
}
\`\`\`

---

### 4.3 Legal Opinion Generation

#### Generate Legal Opinion
\`\`\`
POST /api/v1/sessions/:sessionId/opinion

Request Body:
{
  "include_dissent": boolean  // Include minority opinions
}

Response:
{
  "opinion": LegalOpinionDraft
}
\`\`\`

#### Export Opinion (PDF/DOCX)
\`\`\`
GET /api/v1/sessions/:sessionId/opinion/export?format=pdf|docx

Response: Binary file download
\`\`\`

---

### 4.4 Case Database Search

#### Search Similar Cases
\`\`\`
POST /api/v1/cases/search

Request Body:
{
  "query": string,                     // Natural language query
  "filters": {
    "case_type"?: "narcotics" | "corruption",
    "court_type"?: "district" | "high" | "supreme",
    "date_range"?: { "from": string, "to": string },
    "sentence_range"?: { "min_months": number, "max_months": number },
    "substance_type"?: string,         // For narcotics
    "weight_range"?: { "min_grams": number, "max_grams": number }
  },
  "limit": number,
  "semantic_search": boolean           // Use vector similarity
}

Response:
{
  "cases": CaseRecord[],
  "total": number
}
\`\`\`

#### Get Case Details
\`\`\`
GET /api/v1/cases/:caseId

Response:
{
  "case": CaseRecord
}
\`\`\`

#### Get Case Statistics
\`\`\`
GET /api/v1/cases/statistics?case_type=narcotics&substance=methamphetamine&weight_min=1&weight_max=10

Response:
{
  "total_cases": number,
  "sentence_distribution": {
    "min_months": number,
    "max_months": number,
    "median_months": number,
    "average_months": number,
    "percentiles": { "p25": number, "p50": number, "p75": number }
  },
  "verdict_distribution": {
    "guilty": number,
    "not_guilty": number,
    "rehabilitation": number
  }
}
\`\`\`

---

## 5. AI Agent Specifications

### 5.1 Agent Definitions

Each agent has a distinct persona, reasoning style, and legal philosophy:

#### Agent A: The Strict Constructionist ("Judge Strict")
\`\`\`yaml
persona:
  name: "Strict Constructionist"
  philosophy: "Law must be applied as written"

behavior:
  - Emphasizes statutory interpretation
  - Cites specific articles and their literal meaning
  - Focuses on prosecutor's demands and legal maximums
  - References cases with strict sentencing

triggers:
  - Responds when user asks about "law", "statute", "article", "maximum penalty"
  - Reacts to humanist arguments with counter-points

prompt_template: |
  You are a strict constructionist judge on the Indonesian court system.
  Your role is to interpret the law literally and emphasize statutory requirements.

  Key principles:
  - The law must be applied as written in the statute
  - Sentencing should reflect the severity defined by lawmakers
  - Precedent matters, but statute takes priority
  - Consider the prosecutor's demands seriously

  Current case context: {case_summary}
  Similar cases for reference: {similar_cases}
  Conversation history: {messages}

  Respond to: {user_message}
\`\`\`

#### Agent B: The Humanist ("Judge Humanist")
\`\`\`yaml
persona:
  name: "Rehabilitative Advocate"
  philosophy: "Justice should rehabilitate, not just punish"

behavior:
  - Emphasizes mitigating factors
  - Cites SEMA guidelines for rehabilitation
  - Considers defendant's background and circumstances
  - References restorative justice principles

triggers:
  - Responds when user asks about "rehabilitation", "mitigating", "first offender"
  - Provides counter-balance to strict arguments

prompt_template: |
  You are a humanist judge focused on rehabilitative justice.
  Your role is to consider the human element and reformation potential.

  Key principles:
  - First-time offenders deserve consideration for rehabilitation
  - Mitigating factors must be weighed carefully
  - SEMA No. 4/2010 provides guidance for drug rehabilitation
  - The goal of justice includes reformation, not just punishment

  Current case context: {case_summary}
  Similar cases for reference: {similar_cases}
  Conversation history: {messages}

  Respond to: {user_message}
\`\`\`

#### Agent C: The Historian ("Judge Historian")
\`\`\`yaml
persona:
  name: "Jurisprudence Historian"
  philosophy: "History guides consistent justice"

behavior:
  - Retrieves and cites specific precedent cases
  - Provides statistical context (average sentences, etc.)
  - Identifies landmark cases
  - Highlights sentencing trends over time

triggers:
  - Responds when user asks about "precedent", "similar case", "history", "landmark"
  - Provides factual baseline for debates

prompt_template: |
  You are a jurisprudence historian specializing in Indonesian case law.
  Your role is to provide historical context and cite relevant precedents.

  Key principles:
  - Consistency in sentencing requires knowing historical patterns
  - Landmark cases establish important principles
  - Statistical analysis helps identify appropriate sentence ranges
  - Similar cases should yield similar outcomes

  Current case context: {case_summary}
  Similar cases from database: {similar_cases}
  Relevant statistics: {case_statistics}
  Conversation history: {messages}

  Respond to: {user_message}

  Always cite specific case numbers when referencing precedents.
\`\`\`

### 5.2 Agent Response Logic

\`\`\`typescript
interface AgentResponseContext {
  session: DeliberationSession;
  user_message: DeliberationMessage;
  similar_cases: SimilarCase[];
  case_statistics: CaseStatistics;
  conversation_history: DeliberationMessage[];
}

// Determine which agent(s) should respond
function determineRespondingAgents(
  userMessage: string,
  conversationHistory: DeliberationMessage[]
): AgentId[] {
  const keywords = {
    strict: ["law", "statute", "article", "maximum", "penalty", "prosecutor", "strict"],
    humanist: ["rehabilitation", "mitigating", "first offender", "circumstances", "reform", "humanist"],
    historian: ["precedent", "similar case", "history", "landmark", "statistics", "historian"]
  };

  const message = userMessage.toLowerCase();
  const respondingAgents: AgentId[] = [];

  // Check for direct mentions
  if (message.includes("judge a") || message.includes("strict")) {
    respondingAgents.push("strict");
  }
  if (message.includes("judge b") || message.includes("humanist")) {
    respondingAgents.push("humanist");
  }
  if (message.includes("judge c") || message.includes("historian")) {
    respondingAgents.push("historian");
  }

  // If asking for all opinions or general question
  if (message.includes("all") || message.includes("everyone") ||
      message.includes("what do you think") || respondingAgents.length === 0) {
    // Rotate based on who spoke least recently
    return selectNextSpeaker(conversationHistory);
  }

  return respondingAgents;
}

// Agents should react to each other
function shouldAgentReact(
  agent: AgentId,
  previousMessage: DeliberationMessage
): boolean {
  // Strict reacts to humanist arguments
  if (agent === "strict" && previousMessage.sender.agent_id === "humanist") {
    return containsChallengingContent(previousMessage, "strict");
  }
  // Humanist reacts to strict arguments
  if (agent === "humanist" && previousMessage.sender.agent_id === "strict") {
    return containsChallengingContent(previousMessage, "humanist");
  }
  // Historian provides facts when debate gets heated
  if (agent === "historian" && isDebateHeated(conversationHistory)) {
    return true;
  }
  return false;
}
\`\`\`

### 5.3 Response Generation Flow

\`\`\`
User Message
     │
     ▼
┌─────────────────────────────────┐
│  1. Parse User Intent           │
│  - Extract keywords             │
│  - Identify target agent(s)     │
│  - Classify message type        │
└─────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│  2. Retrieve Context            │
│  - Fetch similar cases          │
│  - Get case statistics          │
│  - Load conversation history    │
└─────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│  3. Determine Responding Agents │
│  - Based on keywords            │
│  - Based on conversation flow   │
│  - Based on reaction rules      │
└─────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│  4. Generate Responses          │
│  - Build agent-specific prompts │
│  - Include relevant cases       │
│  - Generate with LLM            │
└─────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│  5. Post-process & Store        │
│  - Extract cited cases          │
│  - Extract cited laws           │
│  - Save to database             │
│  - Stream to frontend           │
└─────────────────────────────────┘
\`\`\`

---

## 6. Case Similarity Search

### 6.1 Similarity Matching Criteria

For **Narcotics Cases**, match by:
1. Substance type (exact match, high weight)
2. Weight range (within 20% tolerance)
3. Classification (user vs dealer)
4. First offender status
5. Intent (personal use vs distribution)

For **Corruption Cases**, match by:
1. State loss amount range
2. Position/role level
3. Institution type
4. Money laundering involvement
5. Amount returned

### 6.2 Vector Search Implementation

\`\`\`typescript
// Generate embedding for case search
async function generateCaseEmbedding(caseInput: ParsedCaseInput): Promise<number[]> {
  const searchText = buildSearchText(caseInput);
  return await embeddingModel.embed(searchText);
}

function buildSearchText(caseInput: ParsedCaseInput): string {
  const parts = [
    `Case type: ${caseInput.case_type}`,
    `Summary: ${caseInput.summary}`,
    `First offender: ${caseInput.defendant_profile.is_first_offender}`,
    ...caseInput.key_facts
  ];

  if (caseInput.narcotics) {
    parts.push(`Substance: ${caseInput.narcotics.substance}`);
    parts.push(`Weight: ${caseInput.narcotics.weight_grams} grams`);
    parts.push(`Intent: ${caseInput.narcotics.intent}`);
  }

  if (caseInput.corruption) {
    parts.push(`State loss: ${caseInput.corruption.state_loss_idr} IDR`);
    parts.push(`Position: ${caseInput.corruption.position}`);
  }

  return parts.join(". ");
}

// Hybrid search: combine vector similarity with structured filters
async function findSimilarCases(
  caseInput: ParsedCaseInput,
  limit: number = 10
): Promise<SimilarCase[]> {
  const embedding = await generateCaseEmbedding(caseInput);

  const results = await vectorDB.search({
    vector: embedding,
    filter: buildStructuredFilter(caseInput),
    limit: limit,
    include_metadata: true
  });

  return results.map(r => ({
    case_id: r.id,
    case_number: r.metadata.case_number,
    similarity_score: r.score,
    similarity_reason: explainSimilarity(caseInput, r.metadata),
    verdict_summary: r.metadata.verdict_summary,
    sentence_months: r.metadata.sentence_months
  }));
}
\`\`\`

---

## 7. Legal Opinion Generation

### 7.1 Opinion Generation Flow

\`\`\`typescript
async function generateLegalOpinion(
  session: DeliberationSession
): Promise<LegalOpinionDraft> {

  // 1. Analyze conversation for key arguments
  const arguments = extractArguments(session.messages);

  // 2. Get sentence statistics for similar cases
  const statistics = await getCaseStatistics(session.parsed_case);

  // 3. Identify strongest arguments from each side
  const rankedArguments = rankArguments(arguments, session.similar_cases);

  // 4. Calculate recommended sentence range
  const sentenceRange = calculateSentenceRange(
    session.similar_cases,
    statistics,
    session.parsed_case
  );

  // 5. Generate opinion narrative with LLM
  const opinionNarrative = await generateOpinionNarrative({
    case_summary: session.case_input.parsed_case.summary,
    arguments: rankedArguments,
    similar_cases: session.similar_cases,
    sentence_range: sentenceRange
  });

  return {
    session_id: session.id,
    generated_at: new Date().toISOString(),
    case_summary: session.case_input.parsed_case.summary,
    verdict_recommendation: opinionNarrative.verdict,
    sentence_recommendation: sentenceRange,
    legal_arguments: rankedArguments,
    cited_precedents: extractCitedPrecedents(session),
    applicable_laws: extractApplicableLaws(session),
    dissenting_views: extractDissentingViews(arguments)
  };
}
\`\`\`

### 7.2 Sentence Range Calculation

\`\`\`typescript
function calculateSentenceRange(
  similarCases: SimilarCase[],
  statistics: CaseStatistics,
  caseInput: ParsedCaseInput
): SentenceRecommendation {

  // Weight similar cases by similarity score
  const weightedSentences = similarCases.map(c => ({
    months: c.sentence_months,
    weight: c.similarity_score
  }));

  // Calculate weighted average
  const weightedAvg = weightedSentences.reduce(
    (sum, s) => sum + (s.months * s.weight),
    0
  ) / weightedSentences.reduce((sum, s) => sum + s.weight, 0);

  // Apply adjustments based on factors
  let adjustedRecommendation = weightedAvg;

  if (caseInput.defendant_profile.is_first_offender) {
    adjustedRecommendation *= 0.8; // 20% reduction for first offenders
  }

  // Ensure within legal bounds
  const legalBounds = getLegalBounds(caseInput);

  return {
    imprisonment_months: {
      minimum: Math.max(statistics.percentiles.p25, legalBounds.min),
      maximum: Math.min(statistics.percentiles.p75, legalBounds.max),
      recommended: Math.round(adjustedRecommendation)
    },
    fine_idr: calculateFineRange(caseInput, statistics),
    additional_penalties: determineAdditionalPenalties(caseInput)
  };
}
\`\`\`

---

## 8. Database Schema (PostgreSQL)

\`\`\`sql
-- Cases table (imported from your dataset)
CREATE TABLE cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_number VARCHAR(100) UNIQUE NOT NULL,
  case_type VARCHAR(50) NOT NULL,
  court_name VARCHAR(200),
  court_type VARCHAR(50),
  decision_date DATE,

  -- Defendant info
  defendant_name VARCHAR(200),
  defendant_age INTEGER,
  defendant_first_offender BOOLEAN,

  -- Case details (JSONB for flexibility)
  indictment JSONB,
  narcotics_details JSONB,
  corruption_details JSONB,
  legal_facts JSONB,
  verdict JSONB,
  legal_basis JSONB,

  -- Search optimization
  full_text_search TSVECTOR,
  embedding VECTOR(1536),  -- For semantic search

  -- Metadata
  is_landmark_case BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Sessions table
CREATE TABLE deliberation_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  status VARCHAR(20) DEFAULT 'active',

  case_input JSONB NOT NULL,
  similar_case_ids UUID[],

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  concluded_at TIMESTAMP
);

-- Messages table
CREATE TABLE deliberation_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES deliberation_sessions(id) ON DELETE CASCADE,

  sender_type VARCHAR(20) NOT NULL,  -- 'user', 'agent', 'system'
  agent_id VARCHAR(20),              -- 'strict', 'humanist', 'historian'

  content TEXT NOT NULL,
  intent VARCHAR(50),
  cited_case_ids UUID[],
  cited_laws TEXT[],

  created_at TIMESTAMP DEFAULT NOW()
);

-- Legal opinions table
CREATE TABLE legal_opinions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES deliberation_sessions(id) ON DELETE CASCADE,

  opinion_data JSONB NOT NULL,

  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_cases_type ON cases(case_type);
CREATE INDEX idx_cases_date ON cases(decision_date);
CREATE INDEX idx_cases_fts ON cases USING GIN(full_text_search);
CREATE INDEX idx_cases_embedding ON cases USING ivfflat(embedding vector_cosine_ops);
CREATE INDEX idx_sessions_user ON deliberation_sessions(user_id);
CREATE INDEX idx_messages_session ON deliberation_messages(session_id);
\`\`\`

---

## 9. Environment Variables

\`\`\`bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/legal_council
REDIS_URL=redis://host:6379

# Vector Database (for semantic search)
VECTOR_DB_URL=your_vector_db_url
VECTOR_DB_API_KEY=your_api_key

# AI/LLM
OPENAI_API_KEY=your_openai_key
# Or use Vercel AI Gateway
AI_GATEWAY_URL=your_gateway_url

# Authentication (optional)
AUTH_SECRET=your_auth_secret
\`\`\`

---

## 10. Non-Functional Requirements

### Performance
- Case search: < 500ms response time
- Agent response: < 3s for first token (streaming)
- Session load: < 200ms

### Scalability
- Support 1000+ concurrent sessions
- Handle 100,000+ cases in database

### Security
- All sessions tied to authenticated users
- No PII stored in logs
- Case data access controlled by role

### Reliability
- 99.9% uptime target
- Graceful degradation if AI service unavailable
- Session state persisted (no data loss on refresh)

---

## 11. Future Enhancements

1. **PDF Upload & Parsing** - Extract case facts from uploaded indictment PDFs
2. **Voice Input** - Allow judges to dictate case summaries
3. **Multi-language** - Support Bahasa Indonesia interface
4. **Case Outcome Tracking** - Track if recommendations were followed
5. **Collaborative Sessions** - Multiple judges in same deliberation
6. **Mobile App** - For on-the-go case research

