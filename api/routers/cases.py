"""
Case Search and Retrieval Router.

Handles case database queries, search, and statistics.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

import database as db
from schemas import (
    SearchCasesRequest,
    SearchCasesResponse,
    GetCaseResponse,
    CaseStatisticsResponse,
    CaseRecord,
    CaseType,
)
from services.embeddings import get_embedding_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/search", response_model=SearchCasesResponse)
async def search_cases(request: SearchCasesRequest):
    """
    Search for cases using text or semantic search.

    Supports filtering by case type, court type, date range, etc.
    """
    try:
        cases_data = []

        if request.semantic_search:
            # Generate embedding for semantic search
            embedding_service = get_embedding_service()
            query_embedding = await embedding_service.generate_embedding(request.query)

            if query_embedding:
                # Build filters dict
                filters = None
                if request.filters:
                    filters = {
                        "case_type": request.filters.case_type.value
                        if request.filters.case_type
                        else None,
                    }

                cases_data = await db.search_cases_by_vector(
                    query_embedding,
                    filters=filters,
                    limit=request.limit,
                    min_similarity=0.3,
                )
        else:
            # Text-based search
            filters = None
            if request.filters:
                filters = {
                    "case_type": request.filters.case_type.value
                    if request.filters.case_type
                    else None,
                }

            cases_data = await db.search_cases_by_text(
                request.query,
                filters=filters,
                limit=request.limit,
            )

        # Convert to response format
        cases = [_convert_case_record(data) for data in cases_data]

        return SearchCasesResponse(
            cases=cases,
            total=len(cases),
        )

    except Exception as e:
        logger.error(f"Error searching cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=CaseStatisticsResponse)
async def get_case_statistics(
    case_type: str | None = Query(default=None),
    substance: str | None = Query(default=None),
    weight_min: float | None = Query(default=None),
    weight_max: float | None = Query(default=None),
):
    """
    Get aggregated case statistics.

    Returns sentence distributions, verdict breakdowns, etc.
    """
    try:
        stats = await db.get_case_statistics(
            case_type=case_type,
            substance_type=substance,
            weight_min=weight_min,
            weight_max=weight_max,
        )

        return CaseStatisticsResponse(
            total_cases=stats["total_cases"],
            sentence_distribution=stats["sentence_distribution"],
            verdict_distribution=stats["verdict_distribution"],
        )

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}", response_model=GetCaseResponse)
async def get_case(case_id: str):
    """Get a specific case by ID."""
    case_data = await db.get_case_by_id(case_id)

    if not case_data:
        raise HTTPException(status_code=404, detail="Case not found")

    case = _convert_case_record(case_data)
    return GetCaseResponse(case=case)


def _convert_case_record(data: dict[str, Any]) -> CaseRecord:
    """Convert database record to CaseRecord model."""
    extraction = data.get("extraction_result", {}) or {}

    # Extract nested data
    defendant = extraction.get("defendant", {}) or {}
    court = extraction.get("court", {}) or {}
    verdict = extraction.get("verdict", {}) or {}
    case_metadata = extraction.get("case_metadata", {}) or {}

    # Determine case type from metadata
    crime_category = case_metadata.get("crime_category", "").lower()
    case_type = None
    if "korupsi" in crime_category or "corruption" in crime_category:
        case_type = CaseType.CORRUPTION
    elif "narkotika" in crime_category or "narcotics" in crime_category:
        case_type = CaseType.NARCOTICS
    elif crime_category:
        case_type = CaseType.GENERAL_CRIMINAL

    # Get sentence months
    sentences = verdict.get("sentences", {}) or {}
    imprisonment = sentences.get("imprisonment", {}) or {}

    return CaseRecord(
        id=str(data.get("id", "")),
        case_number=data.get("extraction_id") or court.get("verdict_number") or "Unknown",
        case_type=case_type,
        court_name=court.get("court_name"),
        court_type=court.get("court_level"),
        decision_date=verdict.get("date"),
        defendant_name=defendant.get("name"),
        defendant_age=defendant.get("age"),
        defendant_first_offender=None,  # Not directly available in current schema
        indictment=extraction.get("indictment"),
        narcotics_details=None,  # Would need to parse from extraction
        corruption_details=extraction.get("state_loss"),
        legal_facts=extraction.get("legal_facts"),
        verdict=verdict,
        legal_basis=None,  # Would need to extract from indictment
        is_landmark_case=False,
        extraction_result=extraction,
        summary_en=data.get("summary_en"),
        summary_id=data.get("summary_id"),
    )
