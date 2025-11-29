# Legal Council API Integration Guide

This document describes how the frontend should integrate with the backend API for the Legal Council application.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Integration Flow](#integration-flow)
- [Request/Response Examples](#requestresponse-examples)
- [Frontend Implementation Guide](#frontend-implementation-guide)
- [Error Handling](#error-handling)
- [Streaming Implementation](#streaming-implementation)

---

## Overview

### Current State

The frontend currently uses **mock/dummy data** in `council-debate.tsx` instead of calling the actual backend API. The `ApiService` class exists in `src/services/api.ts` but is not utilized by any components.

### Target State

Frontend should call the FastAPI backend at `/api/v1` for:
- Session management (create, list, get, archive)
- Chat/deliberation with AI judges
- Legal opinion generation
- Case search and retrieval

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                     (Next.js 16)                            │
├─────────────────────────────────────────────────────────────┤
│  Components          │  Services         │  State           │
│  ├─ CaseInputForm    │  └─ api.ts       │  └─ Context API  │
│  ├─ CouncilDebate    │     (ApiService)  │                  │
│  └─ LegalOpinion     │                   │                  │
└──────────────────────┴───────────────────┴──────────────────┘
                              │
                              │ HTTP/SSE
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                               │
│                    (FastAPI + Python)                        │
├─────────────────────────────────────────────────────────────┤
│  Routers             │  Services         │  Agents          │
│  ├─ sessions.py      │  ├─ case_parser   │  ├─ Strict       │
│  ├─ cases.py         │  ├─ embeddings    │  ├─ Humanist     │
│  └─ deliberation.py  │  └─ opinion_gen   │  └─ Historian    │
└──────────────────────┴───────────────────┴──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL + pgvector + Vertex AI              │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

**Frontend (`.env.local`):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

**Backend (`.env`):**
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/legal_council
GCP_PROJECT=google-marathon
GCP_REGION=us-central1
```

### API Base URL

| Environment | URL |
|-------------|-----|
| Development | `http://localhost:8000/api/v1` |
| Production  | `https://api.legal-council.com/api/v1` |

---

## API Endpoints

### Session Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sessions` | Create new deliberation session |
| `GET` | `/sessions` | List all sessions (paginated) |
| `GET` | `/sessions/{session_id}` | Get session details |
| `DELETE` | `/sessions/{session_id}` | Archive session (soft delete) |
| `POST` | `/sessions/{session_id}/opinion` | Generate legal opinion |
| `GET` | `/sessions/{session_id}/opinion/export` | Export opinion as PDF/DOCX |

### Deliberation (Chat)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sessions/{session_id}/messages` | Send message, get AI responses |
| `GET` | `/sessions/{session_id}/messages` | Get message history |
| `POST` | `/sessions/{session_id}/messages/stream` | Stream AI responses (SSE) |

### Case Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/cases/search` | Search cases (text or semantic) |
| `GET` | `/cases/{case_id}` | Get specific case details |
| `GET` | `/cases/statistics` | Get aggregated case statistics |

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Basic health check |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/health/live` | Liveness probe |

---

## Integration Flow

### Flow 1: Create Session (User Submits Case)

```
┌──────────────┐     POST /sessions      ┌──────────────┐
│   Frontend   │ ──────────────────────► │   Backend    │
│ CaseInputForm│                         │              │
└──────────────┘                         └──────┬───────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │ 1. Parse case (LLM)   │
                                    │ 2. Generate embedding │
                                    │ 3. Find similar cases │
                                    │ 4. Create session     │
                                    └───────────┬───────────┘
                                                │
┌──────────────┐     Response               │
│   Frontend   │ ◄──────────────────────────┘
│  Navigate to │  {session_id, parsed_case,
│ /deliberation│   similar_cases, initial_message}
└──────────────┘
```

### Flow 2: Chat with AI Judges

```
┌──────────────┐  POST /sessions/{id}/messages  ┌──────────────┐
│   Frontend   │ ─────────────────────────────► │   Backend    │
│ CouncilDebate│  {content, intent, target}     │              │
└──────────────┘                                └──────┬───────┘
                                                       │
                                                       ▼
                                         ┌─────────────────────────┐
                                         │ 1. Save user message    │
                                         │ 2. Determine agents     │
                                         │ 3. Generate responses   │
                                         │    (parallel)           │
                                         │ 4. Save agent messages  │
                                         └───────────┬─────────────┘
                                                     │
┌──────────────┐     Response                        │
│   Frontend   │ ◄───────────────────────────────────┘
│ Update chat  │  {user_message, agent_responses[]}
└──────────────┘
```

### Flow 3: Streaming Chat (Real-time)

```
┌──────────────┐  POST /sessions/{id}/messages/stream  ┌──────────────┐
│   Frontend   │ ────────────────────────────────────► │   Backend    │
│ CouncilDebate│  {content, intent, target}            │              │
└──────────────┘                                       └──────┬───────┘
       ▲                                                      │
       │                                                      ▼
       │                                        ┌─────────────────────────┐
       │         SSE Stream                     │ Generate response       │
       │◄─────────────────────────────────────  │ chunks from agents      │
       │  data: {type: "agent_chunk", ...}      └─────────────────────────┘
       │  data: {type: "agent_chunk", ...}
       │  data: {type: "done"}
```

### Flow 4: Generate Opinion

```
┌──────────────┐  POST /sessions/{id}/opinion  ┌──────────────┐
│   Frontend   │ ────────────────────────────► │   Backend    │
│ CouncilDebate│                               │              │
└──────────────┘                               └──────┬───────┘
                                                      │
                                                      ▼
                                        ┌─────────────────────────┐
                                        │ 1. Fetch all messages   │
                                        │ 2. Synthesize opinion   │
                                        │    (LLM)                │
                                        │ 3. Extract structured   │
                                        │    recommendation       │
                                        │ 4. Save & update status │
                                        └───────────┬─────────────┘
                                                    │
┌──────────────┐     Response                       │
│   Frontend   │ ◄──────────────────────────────────┘
│  Navigate to │  {opinion: LegalOpinionDraft}
│   /opinion   │
└──────────────┘
```

---

## Request/Response Examples

### 1. Create Session

**Request:**
```http
POST /api/v1/sessions
Content-Type: application/json

{
  "input_type": "text_summary",
  "case_summary": "Terdakwa ditangkap membawa 50 gram sabu-sabu untuk diedarkan. Terdakwa merupakan pengedar kelas menengah yang sudah beroperasi selama 2 tahun. Barang bukti ditemukan di rumah terdakwa bersama dengan timbangan digital dan plastik klip.",
  "case_type": "narcotics",
  "structured_data": null
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "parsed_case": {
    "case_type": "narcotics",
    "summary": "Terdakwa ditangkap membawa 50 gram sabu-sabu...",
    "defendant": {
      "name": null,
      "age": null,
      "occupation": "pengedar",
      "prior_convictions": false
    },
    "narcotics": {
      "substance": "methamphetamine",
      "weight_grams": 50.0,
      "intent": "distribution",
      "role": "dealer"
    },
    "charges": [
      {
        "article": "Pasal 114 ayat (2)",
        "law": "UU No. 35 Tahun 2009",
        "description": "Menawarkan untuk dijual, menjual, membeli, menerima..."
      }
    ],
    "key_facts": [
      "Barang bukti 50 gram sabu",
      "Timbangan digital ditemukan",
      "Beroperasi selama 2 tahun"
    ]
  },
  "similar_cases": [
    {
      "id": "case-001",
      "case_number": "123/Pid.Sus/2023/PN Jkt.Sel",
      "similarity_score": 0.89,
      "verdict": "guilty",
      "sentence_months": 48,
      "substance": "methamphetamine",
      "weight_grams": 45.0
    },
    {
      "id": "case-002",
      "case_number": "456/Pid.Sus/2023/PN Bdg",
      "similarity_score": 0.85,
      "verdict": "guilty",
      "sentence_months": 60,
      "substance": "methamphetamine",
      "weight_grams": 55.0
    }
  ],
  "initial_message": {
    "id": "msg-001",
    "sender": {
      "type": "system"
    },
    "content": "Sidang dibuka. Kasus narkotika dengan terdakwa membawa 50 gram sabu-sabu untuk diedarkan telah dicatat. Dewan hakim siap untuk melakukan deliberasi. Silakan ajukan pertanyaan atau minta pendapat dari para hakim.",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 2. Send Message

**Request:**
```http
POST /api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/messages
Content-Type: application/json

{
  "content": "Bagaimana pandangan para hakim mengenai hukuman yang tepat untuk kasus ini?",
  "intent": "ask_opinion",
  "target_agent": "all"
}
```

**Response:**
```json
{
  "user_message": {
    "id": "msg-002",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "sender": {
      "type": "user"
    },
    "content": "Bagaimana pandangan para hakim mengenai hukuman yang tepat untuk kasus ini?",
    "intent": "ask_opinion",
    "timestamp": "2024-01-15T10:31:00Z"
  },
  "agent_responses": [
    {
      "id": "msg-003",
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "sender": {
        "type": "agent",
        "agent_id": "strict",
        "agent_name": "Hakim Teguh"
      },
      "content": "Berdasarkan Pasal 114 ayat (2) UU No. 35 Tahun 2009 tentang Narkotika, untuk kepemilikan sabu-sabu di atas 5 gram dengan tujuan pengedaran, ancaman pidananya adalah penjara seumur hidup atau pidana penjara paling singkat 5 tahun dan paling lama 20 tahun.\n\nDengan barang bukti 50 gram dan bukti pengedaran selama 2 tahun, saya berpendapat hukuman minimal 10 tahun penjara adalah tepat sesuai dengan ketentuan undang-undang.",
      "cited_cases": ["123/Pid.Sus/2023/PN Jkt.Sel"],
      "cited_laws": ["Pasal 114 ayat (2) UU No. 35 Tahun 2009"],
      "timestamp": "2024-01-15T10:31:05Z"
    },
    {
      "id": "msg-004",
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "sender": {
        "type": "agent",
        "agent_id": "humanist",
        "agent_name": "Hakim Welas"
      },
      "content": "Saya setuju bahwa pelanggaran hukum harus dihukum, namun kita juga harus mempertimbangkan aspek rehabilitasi. Apakah terdakwa memiliki ketergantungan narkoba? Apakah ada faktor ekonomi yang mendorong?\n\nProgram rehabilitasi bersamaan dengan hukuman penjara bisa lebih efektif dalam mencegah residivisme. Saya mengusulkan hukuman 6-8 tahun dengan wajib rehabilitasi.",
      "cited_cases": [],
      "cited_laws": ["Pasal 54 UU No. 35 Tahun 2009"],
      "timestamp": "2024-01-15T10:31:10Z"
    },
    {
      "id": "msg-005",
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "sender": {
        "type": "agent",
        "agent_id": "historian",
        "agent_name": "Hakim Sejarah"
      },
      "content": "Berdasarkan analisis 127 kasus serupa dengan karakteristik yang sama (sabu 40-60 gram, pengedar, tanpa catatan kriminal sebelumnya), rata-rata vonis adalah 7.5 tahun penjara.\n\nDistribusi vonis:\n- 5-6 tahun: 23%\n- 7-8 tahun: 45%\n- 9-10 tahun: 25%\n- >10 tahun: 7%\n\nMempertimbangkan preseden, hukuman 7-8 tahun berada dalam range yang konsisten dengan yurisprudensi.",
      "cited_cases": ["123/Pid.Sus/2023/PN Jkt.Sel", "456/Pid.Sus/2023/PN Bdg"],
      "cited_laws": [],
      "timestamp": "2024-01-15T10:31:15Z"
    }
  ]
}
```

### 3. Stream Messages (SSE)

**Request:**
```http
POST /api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/messages/stream
Content-Type: application/json

{
  "content": "Jelaskan lebih detail tentang faktor yang memberatkan",
  "intent": "request_detail",
  "target_agent": "strict"
}
```

**Response (Server-Sent Events):**
```
data: {"type": "user_message", "id": "msg-006", "content": "Jelaskan lebih detail tentang faktor yang memberatkan"}

data: {"type": "agent_start", "agent_id": "strict", "agent_name": "Hakim Teguh"}

data: {"type": "agent_chunk", "agent_id": "strict", "content": "Faktor-faktor yang memberatkan dalam kasus ini meliputi:\n\n"}

data: {"type": "agent_chunk", "agent_id": "strict", "content": "1. **Jumlah barang bukti yang signifikan** - 50 gram sabu-sabu jauh melebihi"}

data: {"type": "agent_chunk", "agent_id": "strict", "content": " batas minimum 5 gram untuk kategori pengedar.\n\n"}

data: {"type": "agent_chunk", "agent_id": "strict", "content": "2. **Durasi aktivitas ilegal** - Terdakwa telah beroperasi selama 2 tahun,"}

data: {"type": "agent_chunk", "agent_id": "strict", "content": " menunjukkan kesengajaan dan bukan tindakan impulsif.\n\n"}

data: {"type": "agent_chunk", "agent_id": "strict", "content": "3. **Bukti pendukung pengedaran** - Ditemukannya timbangan digital dan"}

data: {"type": "agent_chunk", "agent_id": "strict", "content": " plastik klip menguatkan tuduhan pengedaran."}

data: {"type": "agent_complete", "agent_id": "strict", "message_id": "msg-007", "citations": {"cases": [], "laws": ["Pasal 114 ayat (2) UU No. 35 Tahun 2009"]}}

data: {"type": "done"}
```

### 4. Generate Opinion

**Request:**
```http
POST /api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/opinion
Content-Type: application/json

{}
```

**Response:**
```json
{
  "opinion": {
    "id": "opinion-001",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "case_summary": "Terdakwa ditangkap dengan 50 gram sabu-sabu untuk diedarkan. Telah beroperasi sebagai pengedar kelas menengah selama 2 tahun dengan bukti timbangan digital dan plastik klip.",
    "verdict_recommendation": {
      "verdict": "guilty",
      "confidence": 0.95,
      "reasoning": "Bukti yang kuat dan tidak terbantahkan menunjukkan kepemilikan dan pengedaran narkotika golongan I."
    },
    "sentence_recommendation": {
      "min_months": 72,
      "max_months": 120,
      "recommended_months": 96,
      "reasoning": "Mempertimbangkan jumlah barang bukti, durasi aktivitas, dan preseden kasus serupa."
    },
    "legal_arguments": {
      "prosecution": [
        "Barang bukti 50 gram sabu melebihi batas 5 gram untuk kategori pengedar",
        "Bukti fisik timbangan dan plastik klip menguatkan tuduhan pengedaran",
        "Aktivitas selama 2 tahun menunjukkan kesengajaan"
      ],
      "defense": [
        "Tidak ada bukti penjualan langsung kepada konsumen",
        "Terdakwa tidak memiliki catatan kriminal sebelumnya",
        "Potensi untuk rehabilitasi"
      ],
      "court_analysis": [
        "Pasal 114 ayat (2) UU Narkotika berlaku dengan ancaman 5-20 tahun atau seumur hidup",
        "Preseden kasus serupa menunjukkan rata-rata 7-8 tahun",
        "Faktor memberatkan lebih dominan dari faktor meringankan"
      ]
    },
    "cited_precedents": [
      {
        "case_number": "123/Pid.Sus/2023/PN Jkt.Sel",
        "relevance": "Kasus dengan jumlah dan jenis narkotika serupa",
        "outcome": "Vonis 4 tahun penjara",
        "similarity_score": 0.89
      },
      {
        "case_number": "456/Pid.Sus/2023/PN Bdg",
        "relevance": "Pengedar dengan durasi operasi serupa",
        "outcome": "Vonis 5 tahun penjara",
        "similarity_score": 0.85
      }
    ],
    "applicable_laws": [
      {
        "reference": "Pasal 114 ayat (2) UU No. 35 Tahun 2009",
        "description": "Pengedaran narkotika golongan I di atas 5 gram",
        "relevance": "Pasal utama yang dilanggar"
      },
      {
        "reference": "Pasal 132 ayat (1) UU No. 35 Tahun 2009",
        "description": "Percobaan atau permufakatan jahat",
        "relevance": "Potensi pasal tambahan"
      }
    ],
    "dissenting_views": [
      "Hakim Welas berpendapat hukuman 6-8 tahun dengan wajib rehabilitasi lebih tepat untuk tujuan pemulihan."
    ],
    "created_at": "2024-01-15T10:45:00Z"
  },
  "session_status": "concluded"
}
```

### 5. Search Cases

**Request:**
```http
POST /api/v1/cases/search
Content-Type: application/json

{
  "query": "sabu pengedar 50 gram",
  "semantic_search": true,
  "filters": {
    "case_type": "narcotics",
    "substance_type": "methamphetamine",
    "min_weight": 40,
    "max_weight": 60
  },
  "limit": 10,
  "offset": 0
}
```

**Response:**
```json
{
  "cases": [
    {
      "id": "case-001",
      "case_number": "123/Pid.Sus/2023/PN Jkt.Sel",
      "case_type": "narcotics",
      "court": "PN Jakarta Selatan",
      "date": "2023-06-15",
      "verdict": "guilty",
      "sentence_months": 48,
      "narcotics": {
        "substance": "methamphetamine",
        "weight_grams": 45.0,
        "intent": "distribution"
      },
      "similarity_score": 0.89
    },
    {
      "id": "case-002",
      "case_number": "456/Pid.Sus/2023/PN Bdg",
      "case_type": "narcotics",
      "court": "PN Bandung",
      "date": "2023-08-20",
      "verdict": "guilty",
      "sentence_months": 60,
      "narcotics": {
        "substance": "methamphetamine",
        "weight_grams": 55.0,
        "intent": "distribution"
      },
      "similarity_score": 0.85
    }
  ],
  "total": 2,
  "limit": 10,
  "offset": 0
}
```

---

## Frontend Implementation Guide

### Step 1: Update API Service

**File: `src/services/api.ts`**

```typescript
import { config } from '@/lib/config';

const API_BASE_URL = config.api.baseUrl;

export interface CreateSessionRequest {
  input_type: 'text_summary' | 'structured_form' | 'pdf_upload';
  case_summary: string;
  case_type?: 'narcotics' | 'corruption' | 'general_criminal' | 'other';
  structured_data?: Record<string, unknown>;
}

export interface SendMessageRequest {
  content: string;
  intent?: 'present_case' | 'ask_opinion' | 'challenge_argument' | 'request_detail' | 'general';
  target_agent?: 'strict' | 'humanist' | 'historian' | 'all';
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

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  // Health
  async getHealth() {
    return this.request<{ status: string }>('/health');
  }

  // Sessions
  async createSession(data: CreateSessionRequest) {
    return this.request<CreateSessionResponse>('/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getSession(sessionId: string) {
    return this.request<SessionResponse>(`/sessions/${sessionId}`);
  }

  async listSessions(limit = 10, offset = 0) {
    return this.request<ListSessionsResponse>(`/sessions?limit=${limit}&offset=${offset}`);
  }

  async archiveSession(sessionId: string) {
    return this.request<void>(`/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  // Messages
  async sendMessage(sessionId: string, data: SendMessageRequest) {
    return this.request<SendMessageResponse>(`/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMessages(sessionId: string, limit = 50) {
    return this.request<GetMessagesResponse>(`/sessions/${sessionId}/messages?limit=${limit}`);
  }

  // Streaming
  streamMessages(sessionId: string, data: SendMessageRequest): EventSource {
    // Note: For POST with body, use fetch with ReadableStream instead
    // This is a simplified example
    const url = `${this.baseUrl}/sessions/${sessionId}/messages/stream`;
    return new EventSource(url);
  }

  async streamMessagesWithFetch(
    sessionId: string,
    data: SendMessageRequest,
    onChunk: (chunk: StreamChunk) => void,
    onComplete: () => void,
    onError: (error: Error) => void
  ) {
    const url = `${this.baseUrl}/sessions/${sessionId}/messages/stream`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            onChunk(data);
          }
        }
      }

      onComplete();
    } catch (error) {
      onError(error as Error);
    }
  }

  // Opinion
  async generateOpinion(sessionId: string) {
    return this.request<GenerateOpinionResponse>(`/sessions/${sessionId}/opinion`, {
      method: 'POST',
    });
  }

  async exportOpinion(sessionId: string, format: 'pdf' | 'docx') {
    const url = `${this.baseUrl}/sessions/${sessionId}/opinion/export?format=${format}`;
    const response = await fetch(url);
    return response.blob();
  }

  // Cases
  async searchCases(data: SearchCasesRequest) {
    return this.request<SearchCasesResponse>('/cases/search', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getCase(caseId: string) {
    return this.request<CaseResponse>(`/cases/${caseId}`);
  }

  async getCaseStatistics(caseType?: string, substanceType?: string) {
    const params = new URLSearchParams();
    if (caseType) params.set('case_type', caseType);
    if (substanceType) params.set('substance_type', substanceType);
    return this.request<CaseStatisticsResponse>(`/cases/statistics?${params}`);
  }
}

export const apiService = new ApiService(API_BASE_URL);
```

### Step 2: Create Custom Hooks

**File: `src/hooks/useSession.ts`**

```typescript
import { useState, useCallback } from 'react';
import { apiService, CreateSessionRequest } from '@/services/api';

export function useSession() {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createSession = useCallback(async (data: CreateSessionRequest) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.createSession(data);
      setSession(response);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSession = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getSession(sessionId);
      setSession(response);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { session, loading, error, createSession, loadSession };
}
```

**File: `src/hooks/useDeliberation.ts`**

```typescript
import { useState, useCallback } from 'react';
import { apiService, SendMessageRequest, StreamChunk } from '@/services/api';

export function useDeliberation(sessionId: string) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (data: SendMessageRequest) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.sendMessage(sessionId, data);
      setMessages(prev => [
        ...prev,
        response.user_message,
        ...response.agent_responses,
      ]);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const sendMessageStreaming = useCallback(async (data: SendMessageRequest) => {
    setStreaming(true);
    setError(null);

    let currentAgentMessage: Partial<AgentMessage> = {};

    await apiService.streamMessagesWithFetch(
      sessionId,
      data,
      (chunk: StreamChunk) => {
        switch (chunk.type) {
          case 'user_message':
            setMessages(prev => [...prev, chunk as AgentMessage]);
            break;
          case 'agent_start':
            currentAgentMessage = {
              id: `temp-${chunk.agent_id}`,
              agent: chunk.agent_id,
              agentName: chunk.agent_name,
              content: '',
            };
            setMessages(prev => [...prev, currentAgentMessage as AgentMessage]);
            break;
          case 'agent_chunk':
            setMessages(prev => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (updated[lastIdx]?.agent === chunk.agent_id) {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: updated[lastIdx].content + chunk.content,
                };
              }
              return updated;
            });
            break;
          case 'agent_complete':
            setMessages(prev => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (updated[lastIdx]?.agent === chunk.agent_id) {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  id: chunk.message_id,
                  citations: chunk.citations?.cases || [],
                };
              }
              return updated;
            });
            break;
        }
      },
      () => setStreaming(false),
      (err) => {
        setError(err.message);
        setStreaming(false);
      }
    );
  }, [sessionId]);

  const loadMessages = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiService.getMessages(sessionId);
      setMessages(response.messages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load messages');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  return {
    messages,
    loading,
    streaming,
    error,
    sendMessage,
    sendMessageStreaming,
    loadMessages,
  };
}
```

### Step 3: Update Components

**File: `src/components/case-input-form.tsx`** (integration example)

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiService } from '@/services/api';
import { useLegalCouncil } from '@/context/legal-council-context';

export function CaseInputForm() {
  const router = useRouter();
  const { setCaseFacts, setSessionId } = useLegalCouncil();
  const [caseSummary, setCaseSummary] = useState('');
  const [caseType, setCaseType] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await apiService.createSession({
        input_type: 'text_summary',
        case_summary: caseSummary,
        case_type: caseType as any,
      });

      setCaseFacts(caseSummary);
      setSessionId(response.session_id);
      router.push('/deliberation');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields */}
      <button type="submit" disabled={loading}>
        {loading ? 'Memproses...' : 'Mulai Deliberasi'}
      </button>
      {error && <p className="text-red-500">{error}</p>}
    </form>
  );
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Frontend Action |
|------|---------|-----------------|
| 200 | Success | Process response |
| 400 | Bad Request | Show validation error |
| 404 | Not Found | Redirect or show "not found" |
| 422 | Validation Error | Show field-specific errors |
| 500 | Server Error | Show generic error, retry option |

### Error Response Format

```json
{
  "detail": "Session not found",
  "error_code": "SESSION_NOT_FOUND",
  "field": null
}
```

### Frontend Error Handling

```typescript
try {
  const response = await apiService.sendMessage(sessionId, data);
  // Handle success
} catch (error) {
  if (error instanceof Error) {
    if (error.message.includes('404')) {
      // Session not found - redirect to home
      router.push('/');
    } else if (error.message.includes('400')) {
      // Validation error - show message
      setError('Input tidak valid. Silakan periksa kembali.');
    } else {
      // Generic error
      setError('Terjadi kesalahan. Silakan coba lagi.');
    }
  }
}
```

---

## Streaming Implementation

### Using Fetch with ReadableStream

```typescript
async function streamChat(sessionId: string, message: string) {
  const response = await fetch(`/api/v1/sessions/${sessionId}/messages/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: message, target_agent: 'all' }),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) return;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        handleStreamEvent(data);
      }
    }
  }
}

function handleStreamEvent(event: StreamEvent) {
  switch (event.type) {
    case 'agent_start':
      // Add placeholder message
      break;
    case 'agent_chunk':
      // Append content to current message
      break;
    case 'agent_complete':
      // Finalize message with ID and citations
      break;
    case 'done':
      // Stream complete
      break;
  }
}
```

---

## Type Definitions

Add these to `src/types/api.ts`:

```typescript
// Request Types
export interface CreateSessionRequest {
  input_type: 'text_summary' | 'structured_form' | 'pdf_upload';
  case_summary: string;
  case_type?: 'narcotics' | 'corruption' | 'general_criminal' | 'other';
  structured_data?: StructuredCaseData;
}

export interface SendMessageRequest {
  content: string;
  intent?: MessageIntent;
  target_agent?: AgentId | 'all';
}

export interface SearchCasesRequest {
  query: string;
  semantic_search?: boolean;
  filters?: CaseFilters;
  limit?: number;
  offset?: number;
}

// Response Types
export interface CreateSessionResponse {
  session_id: string;
  parsed_case: ParsedCase;
  similar_cases: SimilarCase[];
  initial_message: Message;
  created_at: string;
}

export interface SendMessageResponse {
  user_message: Message;
  agent_responses: Message[];
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

// Stream Types
export type StreamChunk =
  | { type: 'user_message'; id: string; content: string }
  | { type: 'agent_start'; agent_id: AgentId; agent_name: string }
  | { type: 'agent_chunk'; agent_id: AgentId; content: string }
  | { type: 'agent_complete'; agent_id: AgentId; message_id: string; citations?: Citations }
  | { type: 'done' };

// Enums
export type AgentId = 'strict' | 'humanist' | 'historian';
export type MessageIntent = 'present_case' | 'ask_opinion' | 'challenge_argument' | 'request_detail' | 'general';
export type SessionStatus = 'active' | 'concluded' | 'archived';
export type CaseType = 'narcotics' | 'corruption' | 'general_criminal' | 'other';
```

---

## Checklist for Integration

- [ ] Update `src/services/api.ts` with all endpoints
- [ ] Add type definitions in `src/types/api.ts`
- [ ] Create custom hooks (`useSession`, `useDeliberation`, `useOpinion`)
- [ ] Update `LegalCouncilContext` to include `sessionId`
- [ ] Modify `CaseInputForm` to call `createSession`
- [ ] Modify `CouncilDebate` to use real API instead of mock
- [ ] Implement streaming for real-time responses
- [ ] Add error handling and loading states
- [ ] Test all API integrations
- [ ] Update environment variables for production

---

## Related Files

### Backend
- `/api/main.py` - FastAPI application entry point
- `/api/routers/sessions.py` - Session endpoints
- `/api/routers/deliberation.py` - Chat endpoints
- `/api/routers/cases.py` - Case search endpoints
- `/api/schemas.py` - Pydantic request/response models

### Frontend
- `/legal-council-fe/src/services/api.ts` - API client
- `/legal-council-fe/src/context/legal-council-context.tsx` - State management
- `/legal-council-fe/src/components/council-debate.tsx` - Main chat component
- `/legal-council-fe/src/types/` - TypeScript type definitions