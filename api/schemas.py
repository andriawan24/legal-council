"""
Pydantic schemas for Legal Council API request/response models.

Based on PRD specifications from README.md.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class SessionStatus(str, Enum):
    """Deliberation session status."""

    ACTIVE = "active"
    CONCLUDED = "concluded"
    ARCHIVED = "archived"


class InputType(str, Enum):
    """Case input type."""

    TEXT_SUMMARY = "text_summary"
    STRUCTURED_FORM = "structured_form"
    PDF_UPLOAD = "pdf_upload"


class CaseType(str, Enum):
    """Case type classification."""

    NARCOTICS = "narcotics"
    CORRUPTION = "corruption"
    GENERAL_CRIMINAL = "general_criminal"
    OTHER = "other"


class NarcoticsIntent(str, Enum):
    """Narcotics intent classification."""

    PERSONAL_USE = "personal_use"
    DISTRIBUTION = "distribution"
    UNKNOWN = "unknown"


class VerdictDecision(str, Enum):
    """Verdict decision type."""

    GUILTY = "guilty"
    NOT_GUILTY = "not_guilty"
    ACQUITTED = "acquitted"


class AgentId(str, Enum):
    """AI Agent identifiers."""

    STRICT = "strict"
    HUMANIST = "humanist"
    HISTORIAN = "historian"


class MessageIntent(str, Enum):
    """Message intent classification."""

    PRESENT_CASE = "present_case"
    ASK_OPINION = "ask_opinion"
    ASK_PRECEDENT = "ask_precedent"
    CHALLENGE_ARGUMENT = "challenge_argument"
    REQUEST_CLARIFICATION = "request_clarification"
    PROVIDE_ANALYSIS = "provide_analysis"
    CITE_PRECEDENT = "cite_precedent"
    SUMMARIZE = "summarize"


class CourtType(str, Enum):
    """Court type classification."""

    DISTRICT = "district"
    HIGH = "high"
    SUPREME = "supreme"


# =============================================================================
# Nested Models - Case Related
# =============================================================================


class DefendantProfile(BaseModel):
    """Defendant profile information."""

    is_first_offender: bool = True
    age: int | None = None
    occupation: str | None = None


class NarcoticsDetails(BaseModel):
    """Narcotics case specific details."""

    substance: str
    weight_grams: float
    intent: NarcoticsIntent = NarcoticsIntent.UNKNOWN


class CorruptionDetails(BaseModel):
    """Corruption case specific details."""

    state_loss_idr: float
    position: str | None = None


class ParsedCaseInput(BaseModel):
    """Structured parsed case input."""

    case_type: CaseType
    summary: str
    defendant_profile: DefendantProfile
    key_facts: list[str] = Field(default_factory=list)
    charges: list[str] = Field(default_factory=list)
    narcotics: NarcoticsDetails | None = None
    corruption: CorruptionDetails | None = None


class SimilarCase(BaseModel):
    """Similar case from database search."""

    case_id: str
    case_number: str
    similarity_score: float = Field(ge=0, le=1)
    similarity_reason: str
    verdict_summary: str
    sentence_months: int


# =============================================================================
# Message Models
# =============================================================================


class UserSender(BaseModel):
    """User message sender."""

    type: Literal["user"] = "user"
    role: Literal["presiding_judge"] = "presiding_judge"


class AgentSender(BaseModel):
    """Agent message sender."""

    type: Literal["agent"] = "agent"
    agent_id: AgentId


class SystemSender(BaseModel):
    """System message sender."""

    type: Literal["system"] = "system"


MessageSender = UserSender | AgentSender | SystemSender


class DeliberationMessage(BaseModel):
    """Deliberation chat message."""

    id: str
    session_id: str
    sender: MessageSender
    content: str
    intent: MessageIntent | None = None
    cited_cases: list[str] = Field(default_factory=list)
    cited_laws: list[str] = Field(default_factory=list)
    timestamp: datetime


# =============================================================================
# Legal Opinion Models
# =============================================================================


class ArgumentPoint(BaseModel):
    """Single argument point from an agent."""

    argument: str
    source_agent: AgentId
    supporting_cases: list[str] = Field(default_factory=list)
    strength: Literal["strong", "moderate", "weak"] = "moderate"


class CitedPrecedent(BaseModel):
    """Cited precedent case."""

    case_id: str
    case_number: str
    relevance: str
    verdict_summary: str
    how_it_applies: str


class ApplicableLaw(BaseModel):
    """Applicable law reference."""

    law_reference: str
    description: str
    how_it_applies: str


class SentenceRange(BaseModel):
    """Sentence range recommendation."""

    minimum: int
    maximum: int
    recommended: int


class SentenceRecommendation(BaseModel):
    """Full sentence recommendation."""

    imprisonment_months: SentenceRange
    fine_idr: SentenceRange
    additional_penalties: list[str] = Field(default_factory=list)


class VerdictRecommendation(BaseModel):
    """Verdict recommendation."""

    decision: VerdictDecision
    confidence: Literal["high", "medium", "low"]
    reasoning: str


class LegalArguments(BaseModel):
    """Legal arguments from different perspectives."""

    for_conviction: list[ArgumentPoint] = Field(default_factory=list)
    for_leniency: list[ArgumentPoint] = Field(default_factory=list)
    for_severity: list[ArgumentPoint] = Field(default_factory=list)


class LegalOpinionDraft(BaseModel):
    """Generated legal opinion draft."""

    session_id: str
    generated_at: datetime
    case_summary: str
    verdict_recommendation: VerdictRecommendation
    sentence_recommendation: SentenceRecommendation
    legal_arguments: LegalArguments
    cited_precedents: list[CitedPrecedent] = Field(default_factory=list)
    applicable_laws: list[ApplicableLaw] = Field(default_factory=list)
    dissenting_views: list[str] = Field(default_factory=list)


# =============================================================================
# Session Models
# =============================================================================


class CaseInput(BaseModel):
    """Case input from user."""

    input_type: InputType
    raw_input: str
    parsed_case: ParsedCaseInput


class DeliberationSession(BaseModel):
    """Full deliberation session."""

    id: str
    user_id: str | None = None
    status: SessionStatus
    case_input: CaseInput
    similar_cases: list[SimilarCase] = Field(default_factory=list)
    messages: list[DeliberationMessage] = Field(default_factory=list)
    legal_opinion: LegalOpinionDraft | None = None
    created_at: datetime
    updated_at: datetime
    concluded_at: datetime | None = None


# =============================================================================
# Request Models
# =============================================================================


class StructuredCaseData(BaseModel):
    """Optional structured case data for input."""

    defendant_first_offender: bool = True
    defendant_age: int | None = None
    substance_type: str | None = None
    weight_grams: float | None = None
    state_loss_idr: float | None = None


class CreateSessionRequest(BaseModel):
    """Request to create a new deliberation session."""

    input_type: InputType
    case_summary: str
    case_type: CaseType | None = None
    structured_data: StructuredCaseData | None = None


class SendMessageRequest(BaseModel):
    """Request to send a message in a session."""

    content: str
    intent: MessageIntent | None = None
    target_agent: AgentId | Literal["all"] | None = None


class GenerateOpinionRequest(BaseModel):
    """Request to generate a legal opinion."""

    include_dissent: bool = True


class DateRangeFilter(BaseModel):
    """Date range filter."""

    from_date: str | None = Field(None, alias="from")
    to_date: str | None = Field(None, alias="to")


class SentenceRangeFilter(BaseModel):
    """Sentence range filter."""

    min_months: int | None = None
    max_months: int | None = None


class WeightRangeFilter(BaseModel):
    """Weight range filter for narcotics cases."""

    min_grams: float | None = None
    max_grams: float | None = None


class CaseSearchFilters(BaseModel):
    """Filters for case search."""

    case_type: CaseType | None = None
    court_type: CourtType | None = None
    date_range: DateRangeFilter | None = None
    sentence_range: SentenceRangeFilter | None = None
    substance_type: str | None = None
    weight_range: WeightRangeFilter | None = None


class SearchCasesRequest(BaseModel):
    """Request to search for cases."""

    query: str
    filters: CaseSearchFilters | None = None
    limit: int = Field(default=10, ge=1, le=100)
    semantic_search: bool = True


# =============================================================================
# Response Models
# =============================================================================


class CreateSessionResponse(BaseModel):
    """Response for session creation."""

    session_id: str
    parsed_case: ParsedCaseInput
    similar_cases: list[SimilarCase]
    initial_message: DeliberationMessage


class GetSessionResponse(BaseModel):
    """Response for getting a session."""

    session: DeliberationSession


class ListSessionsResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[DeliberationSession]
    pagination: dict[str, int]


class SendMessageResponse(BaseModel):
    """Response for sending a message."""

    user_message: DeliberationMessage
    agent_responses: list[DeliberationMessage]


class GetMessagesResponse(BaseModel):
    """Response for getting messages."""

    messages: list[DeliberationMessage]


class GenerateOpinionResponse(BaseModel):
    """Response for generating an opinion."""

    opinion: LegalOpinionDraft


class CaseRecord(BaseModel):
    """Full case record from database."""

    id: str
    case_number: str
    case_type: CaseType | None = None
    court_name: str | None = None
    court_type: str | None = None
    decision_date: str | None = None
    defendant_name: str | None = None
    defendant_age: int | None = None
    defendant_first_offender: bool | None = None
    indictment: dict[str, Any] | None = None
    narcotics_details: dict[str, Any] | None = None
    corruption_details: dict[str, Any] | None = None
    legal_facts: dict[str, Any] | None = None
    verdict: dict[str, Any] | None = None
    legal_basis: dict[str, Any] | None = None
    is_landmark_case: bool = False
    extraction_result: dict[str, Any] | None = None
    summary_en: str | None = None
    summary_id: str | None = None


class SearchCasesResponse(BaseModel):
    """Response for case search."""

    cases: list[CaseRecord]
    total: int


class GetCaseResponse(BaseModel):
    """Response for getting a single case."""

    case: CaseRecord


class SentenceDistribution(BaseModel):
    """Sentence distribution statistics."""

    min_months: int
    max_months: int
    median_months: float
    average_months: float
    percentiles: dict[str, float]


class VerdictDistribution(BaseModel):
    """Verdict distribution statistics."""

    guilty: int
    not_guilty: int
    rehabilitation: int = 0


class CaseStatisticsResponse(BaseModel):
    """Response for case statistics."""

    total_cases: int
    sentence_distribution: SentenceDistribution
    verdict_distribution: VerdictDistribution


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
    version: str
