"""
Case Parser Service.

Parses user input (text summaries) into structured case data
using LLM extraction.
"""

import json
import logging
from typing import Any

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from config import get_settings
from schemas import (
    ParsedCaseInput,
    DefendantProfile,
    NarcoticsDetails,
    CorruptionDetails,
    CaseType,
    NarcoticsIntent,
    StructuredCaseData,
)

logger = logging.getLogger(__name__)


CASE_PARSING_PROMPT = """You are a legal case analyzer. Parse the following case summary into structured data.

Case Summary:
{case_summary}

Additional Structured Data (if provided):
{structured_data}

Extract the following information and return as JSON:

{{
    "case_type": "narcotics" | "corruption" | "general_criminal" | "other",
    "summary": "Brief 2-3 sentence summary of the case",
    "defendant_profile": {{
        "is_first_offender": true/false,
        "age": number or null,
        "occupation": "string or null"
    }},
    "key_facts": ["fact1", "fact2", ...],  // List of key legal facts
    "charges": ["charge1", "charge2", ...],  // List of charges/articles
    "narcotics": {{  // Only if case_type is "narcotics"
        "substance": "methamphetamine" | "cannabis" | "heroin" | "cocaine" | "ecstasy" | "other",
        "weight_grams": number,
        "intent": "personal_use" | "distribution" | "unknown"
    }},
    "corruption": {{  // Only if case_type is "corruption"
        "state_loss_idr": number,
        "position": "string or null"
    }}
}}

Important:
- Analyze the text carefully to determine case type
- For narcotics cases, look for substance types and weights
- For corruption cases, look for state loss amounts (kerugian negara)
- Extract all relevant charges mentioned
- List key facts that would be relevant for sentencing
- Return ONLY valid JSON, no explanation

JSON Output:"""


class CaseParserService:
    """Service for parsing case summaries into structured data."""

    def __init__(self):
        """Initialize the case parser service."""
        settings = get_settings()
        vertexai.init(project=settings.gcp_project, location=settings.gcp_region)
        self.model = GenerativeModel(settings.vertex_ai_model)
        self.generation_config = GenerationConfig(
            temperature=0.2,  # Lower temperature for more consistent parsing
            top_p=0.95,
            max_output_tokens=2048,
        )

    async def parse_case_summary(
        self,
        case_summary: str,
        case_type: CaseType | None = None,
        structured_data: StructuredCaseData | None = None,
    ) -> ParsedCaseInput:
        """
        Parse a case summary into structured case input.

        Args:
            case_summary: Text description of the case
            case_type: Optional pre-specified case type
            structured_data: Optional additional structured data

        Returns:
            ParsedCaseInput with extracted information
        """
        try:
            # Format structured data if provided
            structured_str = "None provided"
            if structured_data:
                structured_str = json.dumps(structured_data.model_dump(), indent=2)

            prompt = CASE_PARSING_PROMPT.format(
                case_summary=case_summary,
                structured_data=structured_str,
            )

            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.generation_config,
            )

            # Parse JSON response
            response_text = response.text.strip()

            # Clean up response if needed
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            parsed_data = json.loads(response_text.strip())

            # Build ParsedCaseInput from extracted data
            return self._build_parsed_input(
                parsed_data, case_summary, case_type, structured_data
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return self._build_fallback_input(case_summary, case_type, structured_data)

        except Exception as e:
            logger.error(f"Error parsing case summary: {e}")
            return self._build_fallback_input(case_summary, case_type, structured_data)

    def _build_parsed_input(
        self,
        parsed_data: dict[str, Any],
        original_summary: str,
        provided_case_type: CaseType | None,
        structured_data: StructuredCaseData | None,
    ) -> ParsedCaseInput:
        """Build ParsedCaseInput from extracted data."""
        # Determine case type
        case_type_str = parsed_data.get("case_type", "other")
        try:
            case_type = provided_case_type or CaseType(case_type_str)
        except ValueError:
            case_type = CaseType.OTHER

        # Build defendant profile
        defendant_data = parsed_data.get("defendant_profile", {})
        # Handle None values from LLM response - use default if None
        is_first_offender = defendant_data.get("is_first_offender")
        if is_first_offender is None:
            is_first_offender = (
                structured_data.defendant_first_offender
                if structured_data and structured_data.defendant_first_offender is not None
                else True
            )
        defendant_age = defendant_data.get("age")
        if defendant_age is None and structured_data:
            defendant_age = structured_data.defendant_age
        defendant_profile = DefendantProfile(
            is_first_offender=is_first_offender,
            age=defendant_age,
            occupation=defendant_data.get("occupation"),
        )

        # Build narcotics details if applicable
        narcotics = None
        if case_type == CaseType.NARCOTICS:
            narcotics_data = parsed_data.get("narcotics", {})
            substance = narcotics_data.get(
                "substance",
                structured_data.substance_type if structured_data else "unknown",
            )
            weight = narcotics_data.get(
                "weight_grams",
                structured_data.weight_grams if structured_data else 0,
            )
            intent_str = narcotics_data.get("intent", "unknown")
            try:
                intent = NarcoticsIntent(intent_str)
            except ValueError:
                intent = NarcoticsIntent.UNKNOWN

            narcotics = NarcoticsDetails(
                substance=substance or "unknown",
                weight_grams=weight or 0,
                intent=intent,
            )

        # Build corruption details if applicable
        corruption = None
        if case_type == CaseType.CORRUPTION:
            corruption_data = parsed_data.get("corruption", {})
            state_loss = corruption_data.get(
                "state_loss_idr",
                structured_data.state_loss_idr if structured_data else 0,
            )
            corruption = CorruptionDetails(
                state_loss_idr=state_loss or 0,
                position=corruption_data.get("position"),
            )

        return ParsedCaseInput(
            case_type=case_type,
            summary=parsed_data.get("summary", original_summary[:500]),
            defendant_profile=defendant_profile,
            key_facts=parsed_data.get("key_facts", []),
            charges=parsed_data.get("charges", []),
            narcotics=narcotics,
            corruption=corruption,
        )

    def _build_fallback_input(
        self,
        case_summary: str,
        case_type: CaseType | None,
        structured_data: StructuredCaseData | None,
    ) -> ParsedCaseInput:
        """Build a fallback ParsedCaseInput when LLM parsing fails."""
        # Detect case type from keywords if not provided
        detected_type = case_type or CaseType.OTHER
        summary_lower = case_summary.lower()

        if not case_type:
            if any(
                kw in summary_lower
                for kw in ["narkotika", "narcotics", "sabu", "ganja", "heroin"]
            ):
                detected_type = CaseType.NARCOTICS
            elif any(
                kw in summary_lower
                for kw in ["korupsi", "corruption", "kerugian negara", "suap"]
            ):
                detected_type = CaseType.CORRUPTION

        # Build with available structured data - ensure is_first_offender is never None
        is_first_offender = True
        if structured_data and structured_data.defendant_first_offender is not None:
            is_first_offender = structured_data.defendant_first_offender
        defendant_profile = DefendantProfile(
            is_first_offender=is_first_offender,
            age=structured_data.defendant_age if structured_data else None,
        )

        narcotics = None
        if detected_type == CaseType.NARCOTICS and structured_data:
            narcotics = NarcoticsDetails(
                substance=structured_data.substance_type or "unknown",
                weight_grams=structured_data.weight_grams or 0,
                intent=NarcoticsIntent.UNKNOWN,
            )

        corruption = None
        if detected_type == CaseType.CORRUPTION and structured_data:
            corruption = CorruptionDetails(
                state_loss_idr=structured_data.state_loss_idr or 0,
                position=None,
            )

        return ParsedCaseInput(
            case_type=detected_type,
            summary=case_summary[:500],
            defendant_profile=defendant_profile,
            key_facts=[],
            charges=[],
            narcotics=narcotics,
            corruption=corruption,
        )


# Singleton instance
_case_parser_service: CaseParserService | None = None


def get_case_parser_service() -> CaseParserService:
    """Get or create the case parser service singleton."""
    global _case_parser_service
    if _case_parser_service is None:
        _case_parser_service = CaseParserService()
    return _case_parser_service
