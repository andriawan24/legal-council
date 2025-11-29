"""
Session Management Router.

Handles deliberation session CRUD operations.
"""

import logging
from datetime import datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

import database as db
from schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    GetSessionResponse,
    ListSessionsResponse,
    GenerateOpinionRequest,
    GenerateOpinionResponse,
    DeliberationSession,
    DeliberationMessage,
    CaseInput,
    ParsedCaseInput,
    SimilarCase,
    SessionStatus,
    SystemSender,
    InputType,
)
from services.case_parser import get_case_parser_service
from services.embeddings import get_embedding_service
from services.opinion_generator import get_opinion_generator_service
from agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])

# Initialize orchestrator
orchestrator = AgentOrchestrator()


@router.post("", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new deliberation session.

    Parses the case summary, finds similar cases, and initializes the session.
    """
    try:
        # Parse case summary
        parser = get_case_parser_service()
        parsed_case = await parser.parse_case_summary(
            request.case_summary,
            request.case_type,
            request.structured_data,
        )

        # Generate embedding for case search
        embedding_service = get_embedding_service()
        search_text = embedding_service.build_search_text(parsed_case.model_dump())
        query_embedding = await embedding_service.generate_embedding(search_text)

        # Find similar cases
        similar_cases_data = []
        if query_embedding:
            similar_cases_data = await db.search_cases_by_vector(
                query_embedding,
                limit=10,
                min_similarity=0.3,
            )

        # Convert to SimilarCase objects
        similar_cases = []
        for case_data in similar_cases_data[:5]:
            extraction = case_data.get("extraction_result") or {}
            verdict = extraction.get("verdict") or {}
            sentences = verdict.get("sentences") or {}
            imprisonment = sentences.get("imprisonment") or {}

            similar_cases.append(
                SimilarCase(
                    case_id=str(case_data.get("id", "")),
                    case_number=case_data.get("extraction_id", "Unknown"),
                    similarity_score=case_data.get("similarity", 0.5),
                    similarity_reason="Vector similarity match",
                    verdict_summary=verdict.get("result", "Unknown verdict"),
                    sentence_months=imprisonment.get("duration_months", 0) or 0,
                )
            )

        # Build case input
        case_input = CaseInput(
            input_type=request.input_type,
            raw_input=request.case_summary,
            parsed_case=parsed_case,
        )

        # Create session in database
        similar_case_ids = [c.case_id for c in similar_cases]
        session_id = await db.create_session(
            user_id=None,  # TODO: Get from auth
            case_input=case_input.model_dump(),
            similar_case_ids=similar_case_ids,
        )

        # Generate initial system message
        initial_content = orchestrator.get_initial_message_content(
            parsed_case, similar_cases
        )

        # Save initial message
        message_id = await db.create_message(
            session_id=session_id,
            sender_type="system",
            agent_id=None,
            content=initial_content,
            intent="present_case",
        )

        initial_message = DeliberationMessage(
            id=message_id,
            session_id=session_id,
            sender=SystemSender(),
            content=initial_content,
            intent="present_case",
            cited_cases=[],
            cited_laws=[],
            timestamp=datetime.utcnow(),
        )

        return CreateSessionResponse(
            session_id=session_id,
            parsed_case=parsed_case,
            similar_cases=similar_cases,
            initial_message=initial_message,
        )

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=GetSessionResponse)
async def get_session(session_id: str):
    """Get a deliberation session by ID."""
    session_data = await db.get_session(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages for the session
    messages_data = await db.get_messages(session_id)

    # Get legal opinion if exists
    opinion_data = await db.get_legal_opinion(session_id)

    # Convert to response model
    messages = _convert_messages(messages_data)

    # Parse case input
    case_input_data = session_data.get("case_input", {})
    case_input = CaseInput(
        input_type=InputType(case_input_data.get("input_type", "text_summary")),
        raw_input=case_input_data.get("raw_input", ""),
        parsed_case=ParsedCaseInput(**case_input_data.get("parsed_case", {})),
    )

    session = DeliberationSession(
        id=str(session_data["id"]),
        user_id=session_data.get("user_id"),
        status=SessionStatus(session_data.get("status", "active")),
        case_input=case_input,
        similar_cases=[],  # TODO: Fetch similar cases
        messages=messages,
        legal_opinion=opinion_data.get("opinion_data") if opinion_data else None,
        created_at=session_data["created_at"],
        updated_at=session_data["updated_at"],
        concluded_at=session_data.get("concluded_at"),
    )

    return GetSessionResponse(session=session)


@router.get("", response_model=ListSessionsResponse)
async def list_sessions(
    status: Literal["active", "concluded", "all"] = "all",
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List deliberation sessions with optional status filter."""
    sessions_data, total = await db.list_sessions(
        status=status if status != "all" else None,
        page=page,
        limit=limit,
    )

    sessions = []
    for data in sessions_data:
        case_input_data = data.get("case_input", {})

        # Handle missing or invalid case_input
        try:
            case_input = CaseInput(
                input_type=InputType(case_input_data.get("input_type", "text_summary")),
                raw_input=case_input_data.get("raw_input", ""),
                parsed_case=ParsedCaseInput(**case_input_data.get("parsed_case", {})),
            )
        except Exception:
            # Fallback for malformed data
            case_input = CaseInput(
                input_type=InputType.TEXT_SUMMARY,
                raw_input="",
                parsed_case=ParsedCaseInput(
                    case_type="other",
                    summary="",
                    defendant_profile={"is_first_offender": True},
                ),
            )

        sessions.append(
            DeliberationSession(
                id=str(data["id"]),
                user_id=data.get("user_id"),
                status=SessionStatus(data.get("status", "active")),
                case_input=case_input,
                similar_cases=[],
                messages=[],
                legal_opinion=None,
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                concluded_at=data.get("concluded_at"),
            )
        )

    return ListSessionsResponse(
        sessions=sessions,
        pagination={
            "total": total,
            "page": page,
            "limit": limit,
        },
    )


@router.delete("/{session_id}")
async def archive_session(session_id: str):
    """Archive (soft delete) a deliberation session."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    success = await db.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to archive session")

    return {"message": "Session archived successfully"}


@router.post("/{session_id}/opinion", response_model=GenerateOpinionResponse)
async def generate_opinion(session_id: str, request: GenerateOpinionRequest):
    """Generate a legal opinion for the session."""
    # Get session
    session_data = await db.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages
    messages_data = await db.get_messages(session_id, limit=100)
    messages = _convert_messages(messages_data)

    # Parse case input
    case_input_data = session_data.get("case_input", {})
    parsed_case_data = case_input_data.get("parsed_case", {})

    try:
        parsed_case = ParsedCaseInput(**parsed_case_data)
    except Exception:
        parsed_case = None

    # Get similar cases (simplified - would need to fetch full data)
    similar_cases: list[SimilarCase] = []

    # Generate opinion
    generator = get_opinion_generator_service()
    opinion = await generator.generate_opinion(
        session_id=session_id,
        parsed_case=parsed_case,
        similar_cases=similar_cases,
        messages=messages,
        include_dissent=request.include_dissent,
    )

    # Save opinion to database
    await db.save_legal_opinion(session_id, opinion.model_dump())

    # Update session status
    await db.update_session_status(session_id, "concluded")

    return GenerateOpinionResponse(opinion=opinion)


@router.get("/{session_id}/opinion/export")
async def export_opinion(
    session_id: str,
    format: Literal["pdf", "docx"] = "pdf",
):
    """Export the legal opinion as PDF or DOCX."""
    # Get opinion
    opinion_data = await db.get_legal_opinion(session_id)
    if not opinion_data:
        raise HTTPException(status_code=404, detail="No opinion found for this session")

    # TODO: Implement PDF/DOCX generation
    # For now, return a placeholder response
    raise HTTPException(
        status_code=501,
        detail="Export functionality not yet implemented. Use /opinion endpoint for JSON.",
    )


def _convert_messages(messages_data: list[dict]) -> list[DeliberationMessage]:
    """Convert database message records to DeliberationMessage objects."""
    from schemas import UserSender, AgentSender, SystemSender, AgentId

    messages = []
    for msg in messages_data:
        sender_type = msg.get("sender_type", "system")
        agent_id = msg.get("agent_id")

        if sender_type == "user":
            sender = UserSender()
        elif sender_type == "agent" and agent_id:
            try:
                sender = AgentSender(agent_id=AgentId(agent_id))
            except ValueError:
                sender = SystemSender()
        else:
            sender = SystemSender()

        messages.append(
            DeliberationMessage(
                id=str(msg["id"]),
                session_id=str(msg["session_id"]),
                sender=sender,
                content=msg["content"],
                intent=msg.get("intent"),
                cited_cases=msg.get("cited_case_ids") or [],
                cited_laws=msg.get("cited_laws") or [],
                timestamp=msg["created_at"],
            )
        )

    return messages
