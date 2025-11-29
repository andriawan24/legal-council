/**
 * Pengadilan - Court Information
 */
export interface Court {
  city: string;
  province: string;
  court_name: string;
  court_level: string;
  verdict_number: string;
  case_register_number: string;
}

/**
 * Terdakwa - Defendant Information
 */
export interface Defendant {
  name: string; // Nama Lengkap
  alias: string | null; // Nama Panggilan
  patronymic: string | null; // Nama Bin/Binti
  gender: 'Laki-laki' | 'Perempuan';
  age: number | null;
  date_of_birth: string | null; // Format: YYYY-MM-DD
  place_of_birth: string | null;
  citizenship: string; // Kewarganegaraan
  religion: string | null;
  education: string | null; // Pendidikan Terakhir
  occupation: string | null; // Pekerjaan
  address: DefendantAddress;
}

export interface DefendantAddress {
  full_address: string;
  street: string | null;
  rt_rw: string | null;
  kelurahan: string | null;
  kecamatan: string | null;
  city: string | null;
  province: string | null;
}

/**
 * Pasal yang Didakwakan - Cited Legal Articles
 */
export interface CitedArticle {
  article: string;
  law_name: string;
  law_number: string | null;
  law_year: number | null;
  full_citation: string;
}

/**
 * Dakwaan - Indictment
 */
export interface Indictment {
  type: 'Primair' | 'Subsidiair' | 'Tunggal' | 'Kumulatif' | 'Alternatif';
  chronology: string;
  crime_location: string;
  crime_period: {
    start_date: string | null;
    end_date: string | null;
    description: string;
  };
  cited_articles: CitedArticle[];
  defense_exception_status: string | null;
}

/**
 * Kerugian Negara - State Financial Loss (for Corruption cases)
 */
export interface StateLoss {
  currency: string;
  indicted_amount: number;
  proven_amount: number | null;
  returned_amount: number | null;
  remaining_due: number | null;
  auditor: string | null;
  audit_report_number: string | null;
  audit_report_date: string | null;
  perpetrators_proceeds: {
    name: string;
    role: string;
    amount: number | null;
  }[];
}

/**
 * Fakta Hukum - Legal Facts
 */
export interface LegalFacts {
  violations: string[];
  witness_testimonies: string[];
  documentary_evidence: string[];
  other_facts: string[];
  standard_procedures: string[];
  financial_irregularities: string[];
  organizational_structure: string | null;
}

/**
 * Personel Pengadilan - Court Personnel
 */
export interface CourtPersonnel {
  judges: {
    name: string;
    role: 'Hakim Ketua' | 'Hakim Anggota' | 'Hakim Ad. Hoc Tipikor';
  }[];
  prosecutors: {
    name: string;
    role: string;
  }[];
  court_clerks: {
    name: string;
    role: string;
  }[];
}

/**
 * Penasihat Hukum - Legal Counsel/Defense Lawyer
 */
export interface LegalCounsel {
  name: string;
  office_name: string;
  office_address: string;
}

/**
 * Tuntutan Jaksa - Prosecution Demand
 */
export interface ProsecutionDemand {
  date: string | null;
  content: string;
  articles: CitedArticle[];
  prison_sentence_months: number | null;
  prison_sentence_description: string | null;
  fine_amount: number | null;
  fine_subsidiary_confinement_months: number | null;
  restitution_amount: number | null;
  restitution_subsidiary_type: string | null;
  restitution_subsidiary_duration_months: number | null;
}

/**
 * Putusan - Verdict
 */
export interface Verdict {
  number: string;
  year: number;
  date: string | null;
  day: string | null;
  result: 'Bebas' | 'Lepas' | 'Pidana' | null;
  sentences: VerdictSentence[] | null;
  proven_articles: CitedArticle[];
  ruling_contents: string[];
  primary_charge_proven: boolean | null;
  subsidiary_charge_proven: boolean | null;
}

export interface VerdictSentence {
  type: 'Penjara' | 'Denda' | 'Uang Pengganti' | 'Kurungan' | 'Pidana Tambahan';
  duration_months?: number;
  amount?: number;
  description: string;
}

/**
 * Pertimbangan Hakim - Judicial Considerations
 */
export interface JudicialConsiderations {
  legal_element_considerations: string[];
  aggravating_factors: string[];
  mitigating_factors: string[];
}

/**
 * Riwayat Penahanan - Detention History
 */
export interface DetentionRecord {
  stage: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  location: string;
}

/**
 * Metadata Perkara - Case Metadata
 */
export interface CaseMetadata {
  crime_category: string;
  crime_subcategory: string | null;
  institution_involved: string | null;
  related_cases: string[];
}

/**
 * Data Tambahan Perkara - Additional Case Data
 */
export interface AdditionalCaseData {
  detention_history: DetentionRecord[];
  appeal_process: string | null;
  evidence_inventory: string[] | null;
  lower_court_decision: string | null;
}

// ===========================================
// COMPLETE CASE RECORD (matches dataset)
// ===========================================

/**
 * Perkara Lengkap - Complete Case Record from Database
 * This matches the structure of the provided dataset
 */
export interface CaseRecord {
  court: Court;
  verdict: Verdict;

  defendant: Defendant;
  legal_counsels: LegalCounsel[];
  court_personnel: CourtPersonnel;

  indictment: Indictment;
  legal_facts: LegalFacts;
  case_metadata: CaseMetadata;

  state_loss: StateLoss | null;

  prosecution_demand: ProsecutionDemand;
  judicial_considerations: JudicialConsiderations;
  additional_case_data: AdditionalCaseData;

  extraction_confidence: number;
}

// ===========================================
// DELIBERATION SESSION TYPES
// ===========================================

/**
 * Anggota Dewan - Council Member (AI Agent)
 */
export type CouncilMemberRole = 'penafsir_ketat' | 'rehabilitatif' | 'ahli_yurisprudensi';

export interface CouncilMember {
  id: CouncilMemberRole;
  name: string;
  title: string;
  description: string;
  perspective: string;
  avatar_color: string;
}

/**
 * Pesan Deliberasi - Deliberation Message
 */
export type MessageSender = CouncilMemberRole | 'user' | 'system';

export interface DeliberationMessage {
  id: string;
  sender: MessageSender;
  sender_name: string; // Display name
  content: string;
  timestamp: Date;

  // Optional references to case data
  cited_articles?: CitedArticle[];
  referenced_precedents?: CasePrecedent[];
  referenced_evidence?: string[];
}

/**
 * Yurisprudensi - Case Precedent for reference
 */
export interface CasePrecedent {
  verdict_number: string;
  court_name: string;
  year: number;
  crime_category: string;
  summary: string;
  relevance_score: number; // 0-1 how relevant to current case
  sentence_outcome: string;
}

/**
 * Sesi Musyawarah - Deliberation Session
 */
export type SessionStatus =
  | 'input' // User entering case
  | 'deliberating' // Agents discussing
  | 'awaiting_user' // Waiting for user input
  | 'generating_opinion' // Creating final opinion
  | 'completed'; // Session finished

export interface DeliberationSession {
  id: string;
  created_at: Date;
  updated_at: Date;
  status: SessionStatus;

  // The case being deliberated
  case_input: CaseInput;

  // Related historical cases from database
  similar_cases: CaseRecord[];

  // Conversation history
  messages: DeliberationMessage[];

  // Final output
  legal_opinion: LegalOpinionDraft | null;
}

/**
 * Input Perkara - Case Input (what user provides)
 */
export interface CaseInput {
  // Basic info
  crime_category: CaseMetadata['crime_category'];
  summary: string; // User's description of the case

  // Optional structured data (if user uploads PDF)
  defendant_name?: string;
  cited_articles?: CitedArticle[];
  prosecution_demand_summary?: string;
  state_loss_amount?: number;

  // Source
  source_type: 'manual' | 'pdf_upload' | 'case_selection';
  source_case_id?: string; // If selected from database
}

// ===========================================
// LEGAL OPINION OUTPUT
// ===========================================

/**
 * Draft Pendapat Hukum - Legal Opinion Draft
 */
export interface LegalOpinionDraft {
  generated_at: Date;

  // Recommendation
  recommended_verdict: 'Bebas' | 'Lepas' | 'Pidana';

  // Sentencing range
  sentence_range: {
    minimum_months: number;
    maximum_months: number;
    recommended_months: number;
    fine_range?: {
      minimum: number;
      maximum: number;
      recommended: number;
    };
    restitution?: number;
  };

  // Supporting arguments from each perspective
  arguments: {
    from_strict_constructionist: string[];
    from_rehabilitative: string[];
    from_jurisprudence: string[];
  };

  // Legal basis
  applicable_articles: CitedArticle[];
  cited_precedents: CasePrecedent[];

  // Considerations
  aggravating_factors: string[];
  mitigating_factors: string[];

  // Confidence and disclaimer
  confidence_score: number; // 0-1
  disclaimer: string;
}

// ===========================================
// SEARCH & FILTER TYPES
// ===========================================

/**
 * Filter Pencarian - Search Filters for finding similar cases
 */
export interface CaseSearchFilters {
  crime_category?: CaseMetadata['crime_category'];
  crime_subcategory?: string;
  court_level?: string;
  province?: string;
  year_range?: {
    from: number;
    to: number;
  };
  sentence_range_months?: {
    min: number;
    max: number;
  };
  state_loss_range?: {
    min: number;
    max: number;
  };
  cited_articles?: string[]; // Filter by specific articles
  keywords?: string[];
}

/**
 * Hasil Pencarian - Search Result
 */
export interface CaseSearchResult {
  case: CaseRecord;
  relevance_score: number;
  matched_criteria: string[];
}

// ===========================================
// COUNCIL MEMBER DEFINITIONS (Constants)
// ===========================================

export const COUNCIL_MEMBERS: Record<CouncilMemberRole, CouncilMember> = {
  penafsir_ketat: {
    id: 'penafsir_ketat',
    name: 'Hakim A',
    title: 'Penafsir Ketat',
    description: 'Strict Constructionist - focuses on literal interpretation of the law',
    perspective:
      'Menganalisis berdasarkan bunyi pasal secara tekstual dan yurisprudensi yang konsisten',
    avatar_color: 'red',
  },
  rehabilitatif: {
    id: 'rehabilitatif',
    name: 'Hakim B',
    title: 'Pendekatan Rehabilitatif',
    description: 'Humanist - emphasizes rehabilitation and mitigating factors',
    perspective: 'Mempertimbangkan aspek kemanusiaan, rehabilitasi, dan hal-hal yang meringankan',
    avatar_color: 'green',
  },
  ahli_yurisprudensi: {
    id: 'ahli_yurisprudensi',
    name: 'Hakim C',
    title: 'Ahli Yurisprudensi',
    description: 'Historian - references landmark precedents and case comparisons',
    perspective: 'Membandingkan dengan putusan-putusan serupa dan yurisprudensi Mahkamah Agung',
    avatar_color: 'blue',
  },
};
