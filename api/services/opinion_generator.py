"""
Legal Opinion Generator Service.

Generates structured legal opinions based on deliberation sessions.
"""

import json
import logging
from datetime import datetime
from typing import Any

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from config import get_settings
from schemas import (
    LegalOpinionDraft,
    VerdictRecommendation,
    SentenceRecommendation,
    SentenceRange,
    LegalArguments,
    ArgumentPoint,
    CitedPrecedent,
    ApplicableLaw,
    AgentId,
    VerdictDecision,
    DeliberationMessage,
    SimilarCase,
    ParsedCaseInput,
)

logger = logging.getLogger(__name__)


OPINION_GENERATION_PROMPT = """You are a legal opinion synthesizer. Based on the deliberation below, generate a comprehensive legal opinion draft.

## Case Summary
{case_summary}

## Similar Cases Referenced
{similar_cases}

## Deliberation Messages
{messages}

## Task
Generate a structured legal opinion that synthesizes all perspectives discussed.

Return the opinion as JSON with this structure:
{{
    "case_summary": "Brief summary of the case",
    "verdict_recommendation": {{
        "decision": "guilty" | "not_guilty" | "acquitted",
        "confidence": "high" | "medium" | "low",
        "reasoning": "Explanation of verdict recommendation"
    }},
    "sentence_recommendation": {{
        "imprisonment_months": {{
            "minimum": number,
            "maximum": number,
            "recommended": number
        }},
        "fine_idr": {{
            "minimum": number,
            "maximum": number,
            "recommended": number
        }},
        "additional_penalties": ["penalty1", "penalty2"]
    }},
    "legal_arguments": {{
        "for_conviction": [
            {{
                "argument": "Argument text",
                "source_agent": "strict" | "humanist" | "historian",
                "supporting_cases": ["case_number1"],
                "strength": "strong" | "moderate" | "weak"
            }}
        ],
        "for_leniency": [...],
        "for_severity": [...]
    }},
    "cited_precedents": [
        {{
            "case_id": "uuid or case number",
            "case_number": "formal case number",
            "relevance": "Why this case is relevant",
            "verdict_summary": "Brief verdict summary",
            "how_it_applies": "How it applies to current case"
        }}
    ],
    "applicable_laws": [
        {{
            "law_reference": "UU No. X Tahun YYYY Pasal Z",
            "description": "What the law covers",
            "how_it_applies": "How it applies here"
        }}
    ],
    "dissenting_views": ["View 1", "View 2"]  // Minority opinions
}}

Important:
- Synthesize arguments from all three judicial perspectives
- Base sentence recommendations on similar cases
- Include dissenting views if {include_dissent}
- Be specific about legal citations
- Return ONLY valid JSON

JSON Output:"""


class OpinionGeneratorService:
    """Service for generating legal opinions from deliberation sessions."""

    def __init__(self):
        """Initialize the opinion generator service."""
        settings = get_settings()
        vertexai.init(project=settings.gcp_project, location=settings.gcp_region)
        self.model = GenerativeModel(settings.vertex_ai_model)
        self.generation_config = GenerationConfig(
            temperature=0.3,
            top_p=0.95,
            max_output_tokens=4096,
        )

    async def generate_opinion(
        self,
        session_id: str,
        parsed_case: ParsedCaseInput | None,
        similar_cases: list[SimilarCase],
        messages: list[DeliberationMessage],
        include_dissent: bool = True,
    ) -> LegalOpinionDraft:
        """
        Generate a legal opinion from the deliberation session.

        Args:
            session_id: The session ID
            parsed_case: Parsed case information
            similar_cases: Similar cases from database
            messages: Deliberation messages
            include_dissent: Whether to include dissenting views

        Returns:
            LegalOpinionDraft with synthesized opinion
        """
        try:
            # Build case summary
            case_summary = self._build_case_summary(parsed_case)

            # Format similar cases
            similar_cases_text = self._format_similar_cases(similar_cases)

            # Format messages
            messages_text = self._format_messages(messages)

            prompt = OPINION_GENERATION_PROMPT.format(
                case_summary=case_summary,
                similar_cases=similar_cases_text,
                messages=messages_text,
                include_dissent=str(include_dissent).lower(),
            )

            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.generation_config,
            )

            # Parse JSON response
            response_text = response.text.strip()

            # Clean up response
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            parsed_data = json.loads(response_text.strip())

            return self._build_opinion(session_id, parsed_data, include_dissent)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse opinion JSON: {e}")
            return self._build_fallback_opinion(
                session_id, parsed_case, similar_cases, messages
            )

        except Exception as e:
            logger.error(f"Error generating opinion: {e}")
            return self._build_fallback_opinion(
                session_id, parsed_case, similar_cases, messages
            )

    def _build_case_summary(self, parsed_case: ParsedCaseInput | None) -> str:
        """Build case summary text."""
        if not parsed_case:
            return "No case details available."

        parts = [
            f"Case Type: {parsed_case.case_type.value}",
            f"Summary: {parsed_case.summary}",
        ]

        if parsed_case.defendant_profile:
            status = (
                "First offender"
                if parsed_case.defendant_profile.is_first_offender
                else "Repeat offender"
            )
            parts.append(f"Defendant: {status}")

        if parsed_case.key_facts:
            parts.append(f"Key Facts: {', '.join(parsed_case.key_facts[:5])}")

        if parsed_case.narcotics:
            n = parsed_case.narcotics
            parts.append(f"Narcotics: {n.substance}, {n.weight_grams}g, {n.intent.value}")

        if parsed_case.corruption:
            c = parsed_case.corruption
            parts.append(f"State Loss: IDR {c.state_loss_idr:,.0f}")

        return "\n".join(parts)

    def _format_similar_cases(self, similar_cases: list[SimilarCase]) -> str:
        """Format similar cases for the prompt."""
        if not similar_cases:
            return "No similar cases found."

        lines = []
        for case in similar_cases[:5]:
            lines.append(
                f"- {case.case_number}: {case.verdict_summary} "
                f"(Sentence: {case.sentence_months} months, "
                f"Similarity: {case.similarity_score:.0%})"
            )
        return "\n".join(lines)

    def _format_messages(self, messages: list[DeliberationMessage]) -> str:
        """Format deliberation messages for the prompt."""
        if not messages:
            return "No deliberation messages."

        lines = []
        for msg in messages[-20:]:  # Last 20 messages
            sender_name = self._get_sender_name(msg.sender)
            lines.append(f"{sender_name}: {msg.content[:500]}")
        return "\n\n".join(lines)

    def _get_sender_name(self, sender: Any) -> str:
        """Get display name for sender."""
        if hasattr(sender, "type"):
            if sender.type == "user":
                return "Presiding Judge"
            elif sender.type == "agent":
                names = {
                    AgentId.STRICT: "Judge Strict",
                    AgentId.HUMANIST: "Judge Humanist",
                    AgentId.HISTORIAN: "Judge Historian",
                }
                return names.get(sender.agent_id, "Judge")
            elif sender.type == "system":
                return "System"
        return "Unknown"

    def _build_opinion(
        self,
        session_id: str,
        data: dict[str, Any],
        include_dissent: bool,
    ) -> LegalOpinionDraft:
        """Build LegalOpinionDraft from parsed data."""
        # Parse verdict recommendation
        verdict_data = data.get("verdict_recommendation", {})
        try:
            decision = VerdictDecision(verdict_data.get("decision", "guilty"))
        except ValueError:
            decision = VerdictDecision.GUILTY

        verdict_recommendation = VerdictRecommendation(
            decision=decision,
            confidence=verdict_data.get("confidence", "medium"),
            reasoning=verdict_data.get("reasoning", "Based on deliberation"),
        )

        # Parse sentence recommendation
        sentence_data = data.get("sentence_recommendation", {})
        imprisonment = sentence_data.get("imprisonment_months", {})
        fine = sentence_data.get("fine_idr", {})

        sentence_recommendation = SentenceRecommendation(
            imprisonment_months=SentenceRange(
                minimum=imprisonment.get("minimum", 0),
                maximum=imprisonment.get("maximum", 0),
                recommended=imprisonment.get("recommended", 0),
            ),
            fine_idr=SentenceRange(
                minimum=fine.get("minimum", 0),
                maximum=fine.get("maximum", 0),
                recommended=fine.get("recommended", 0),
            ),
            additional_penalties=sentence_data.get("additional_penalties", []),
        )

        # Parse legal arguments
        args_data = data.get("legal_arguments", {})
        legal_arguments = LegalArguments(
            for_conviction=self._parse_arguments(args_data.get("for_conviction", [])),
            for_leniency=self._parse_arguments(args_data.get("for_leniency", [])),
            for_severity=self._parse_arguments(args_data.get("for_severity", [])),
        )

        # Parse cited precedents
        precedents = []
        for p in data.get("cited_precedents", []):
            precedents.append(
                CitedPrecedent(
                    case_id=p.get("case_id", ""),
                    case_number=p.get("case_number", ""),
                    relevance=p.get("relevance", ""),
                    verdict_summary=p.get("verdict_summary", ""),
                    how_it_applies=p.get("how_it_applies", ""),
                )
            )

        # Parse applicable laws
        laws = []
        for law in data.get("applicable_laws", []):
            laws.append(
                ApplicableLaw(
                    law_reference=law.get("law_reference", ""),
                    description=law.get("description", ""),
                    how_it_applies=law.get("how_it_applies", ""),
                )
            )

        # Dissenting views
        dissenting = data.get("dissenting_views", []) if include_dissent else []

        return LegalOpinionDraft(
            session_id=session_id,
            generated_at=datetime.utcnow(),
            case_summary=data.get("case_summary", ""),
            verdict_recommendation=verdict_recommendation,
            sentence_recommendation=sentence_recommendation,
            legal_arguments=legal_arguments,
            cited_precedents=precedents,
            applicable_laws=laws,
            dissenting_views=dissenting,
        )

    def _parse_arguments(self, args_list: list[dict]) -> list[ArgumentPoint]:
        """Parse argument points from data."""
        arguments = []
        for arg in args_list:
            try:
                source = AgentId(arg.get("source_agent", "historian"))
            except ValueError:
                source = AgentId.HISTORIAN

            arguments.append(
                ArgumentPoint(
                    argument=arg.get("argument", ""),
                    source_agent=source,
                    supporting_cases=arg.get("supporting_cases", []),
                    strength=arg.get("strength", "moderate"),
                )
            )
        return arguments

    def _build_fallback_opinion(
        self,
        session_id: str,
        parsed_case: ParsedCaseInput | None,
        similar_cases: list[SimilarCase],
        messages: list[DeliberationMessage],
    ) -> LegalOpinionDraft:
        """Build a fallback opinion when generation fails."""
        # Calculate average sentence from similar cases
        avg_sentence = 0
        if similar_cases:
            avg_sentence = sum(c.sentence_months for c in similar_cases) // len(
                similar_cases
            )

        return LegalOpinionDraft(
            session_id=session_id,
            generated_at=datetime.utcnow(),
            case_summary=parsed_case.summary if parsed_case else "Case summary unavailable",
            verdict_recommendation=VerdictRecommendation(
                decision=VerdictDecision.GUILTY,
                confidence="low",
                reasoning="Unable to generate detailed analysis. Please review manually.",
            ),
            sentence_recommendation=SentenceRecommendation(
                imprisonment_months=SentenceRange(
                    minimum=max(0, avg_sentence - 12),
                    maximum=avg_sentence + 12,
                    recommended=avg_sentence,
                ),
                fine_idr=SentenceRange(minimum=0, maximum=0, recommended=0),
                additional_penalties=[],
            ),
            legal_arguments=LegalArguments(),
            cited_precedents=[],
            applicable_laws=[],
            dissenting_views=["Opinion generation encountered an error. Manual review required."],
        )


# Singleton instance
_opinion_generator: OpinionGeneratorService | None = None


def get_opinion_generator_service() -> OpinionGeneratorService:
    """Get or create the opinion generator service singleton."""
    global _opinion_generator
    if _opinion_generator is None:
        _opinion_generator = OpinionGeneratorService()
    return _opinion_generator
