"""
Deliberation (Chat) Router.

Handles message sending and retrieval for deliberation sessions.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

import database as db
from schemas import (
    SendMessageRequest,
    SendMessageResponse,
    GetMessagesResponse,
    DeliberationMessage,
    UserSender,
    AgentSender,
    SystemSender,
    AgentId,
    ParsedCaseInput,
    SimilarCase,
)
from agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions/{session_id}/messages", tags=["deliberation"])

# Initialize orchestrator
orchestrator = AgentOrchestrator()


@router.post("", response_model=SendMessageResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """
    Send a message and receive agent responses.

    The AI agents will analyze the message and respond based on context.
    """
    # Verify session exists
    session_data = await db.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_data.get("status") != "active":
        raise HTTPException(
            status_code=400, detail="Session is not active. Create a new session."
        )

    try:
        # Save user message
        user_message_id = await db.create_message(
            session_id=session_id,
            sender_type="user",
            agent_id=None,
            content=request.content,
            intent=request.intent.value if request.intent else None,
        )

        user_message = DeliberationMessage(
            id=user_message_id,
            session_id=session_id,
            sender=UserSender(),
            content=request.content,
            intent=request.intent,
            cited_cases=[],
            cited_laws=[],
            timestamp=datetime.utcnow(),
        )

        # Get conversation history
        messages_data = await db.get_messages(session_id, limit=50)
        conversation_history = _convert_messages(messages_data)

        # Parse case input from session
        case_input_data = session_data.get("case_input", {})
        parsed_case_data = case_input_data.get("parsed_case", {})

        try:
            parsed_case = ParsedCaseInput(**parsed_case_data)
        except Exception:
            parsed_case = None

        # Get similar cases (simplified)
        similar_cases = await _get_similar_cases(session_data)

        # Get case statistics
        case_statistics = None
        if parsed_case:
            case_statistics = await db.get_case_statistics(
                case_type=parsed_case.case_type.value
            )

        # Generate agent responses
        target_agent = None
        if request.target_agent:
            if request.target_agent == "all":
                target_agent = "all"
            else:
                try:
                    target_agent = AgentId(request.target_agent)
                except ValueError:
                    pass

        agent_responses = await orchestrator.generate_responses(
            user_message=request.content,
            target_agent=target_agent,
            parsed_case=parsed_case,
            similar_cases=similar_cases,
            case_statistics=case_statistics,
            conversation_history=conversation_history,
        )

        # Save agent responses and convert to messages
        response_messages = []
        for response in agent_responses:
            message_id = await db.create_message(
                session_id=session_id,
                sender_type="agent",
                agent_id=response.agent_id.value,
                content=response.content,
                intent=response.intent,
                cited_case_ids=response.cited_cases,
                cited_laws=response.cited_laws,
            )

            response_messages.append(
                DeliberationMessage(
                    id=message_id,
                    session_id=session_id,
                    sender=AgentSender(agent_id=response.agent_id),
                    content=response.content,
                    intent=response.intent,
                    cited_cases=response.cited_cases,
                    cited_laws=response.cited_laws,
                    timestamp=datetime.utcnow(),
                )
            )

        return SendMessageResponse(
            user_message=user_message,
            agent_responses=response_messages,
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=GetMessagesResponse)
async def get_messages(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    before: str | None = Query(default=None),
):
    """Get message history for a session."""
    # Verify session exists
    session_data = await db.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    messages_data = await db.get_messages(
        session_id=session_id,
        limit=limit,
        before_id=before,
    )

    messages = _convert_messages(messages_data)

    return GetMessagesResponse(messages=messages)


@router.post("/stream")
async def send_message_stream(session_id: str, request: SendMessageRequest):
    """
    Send a message and receive streaming agent responses.

    Uses Server-Sent Events (SSE) to stream responses.
    """
    # Verify session exists
    session_data = await db.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_data.get("status") != "active":
        raise HTTPException(
            status_code=400, detail="Session is not active."
        )

    async def generate():
        """Generate SSE stream."""
        import json

        try:
            # Save user message
            user_message_id = await db.create_message(
                session_id=session_id,
                sender_type="user",
                agent_id=None,
                content=request.content,
                intent=request.intent.value if request.intent else None,
            )

            # Send user message event
            user_msg_data = {
                "type": "user_message",
                "id": user_message_id,
                "content": request.content,
            }
            yield f"data: {json.dumps(user_msg_data)}\n\n"

            # Get conversation history
            messages_data = await db.get_messages(session_id, limit=50)
            conversation_history = _convert_messages(messages_data)

            # Parse case input
            case_input_data = session_data.get("case_input", {})
            parsed_case_data = case_input_data.get("parsed_case", {})

            try:
                parsed_case = ParsedCaseInput(**parsed_case_data)
            except Exception:
                parsed_case = None

            similar_cases = await _get_similar_cases(session_data)

            # Determine responding agents
            target_agent = None
            if request.target_agent and request.target_agent != "all":
                try:
                    target_agent = AgentId(request.target_agent)
                except ValueError:
                    pass

            responding_agents = orchestrator.determine_responding_agents(
                request.content, target_agent, conversation_history
            )

            # Stream each agent's response
            for agent_id in responding_agents:
                agent = orchestrator.agents[agent_id]

                # Send agent start event
                start_data = {
                    "type": "agent_start",
                    "agent_id": agent_id.value,
                    "agent_name": agent.name,
                }
                yield f"data: {json.dumps(start_data)}\n\n"

                # Build context
                from agents.base import AgentContext

                context = AgentContext(
                    case_summary=orchestrator._build_case_summary(
                        parsed_case, similar_cases
                    ),
                    parsed_case=parsed_case,
                    similar_cases=similar_cases,
                    case_statistics=None,
                    conversation_history=conversation_history,
                    user_message=request.content,
                )

                # Stream agent response
                full_content = ""
                async for chunk in agent.generate_response_stream(context):
                    full_content += chunk
                    chunk_data = {
                        "type": "agent_chunk",
                        "agent_id": agent_id.value,
                        "content": chunk,
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                # Save complete message
                message_id = await db.create_message(
                    session_id=session_id,
                    sender_type="agent",
                    agent_id=agent_id.value,
                    content=full_content,
                )

                # Send agent complete event
                complete_data = {
                    "type": "agent_complete",
                    "agent_id": agent_id.value,
                    "message_id": message_id,
                }
                yield f"data: {json.dumps(complete_data)}\n\n"

            # Send done event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Error in stream: {e}")
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


def _convert_messages(messages_data: list[dict]) -> list[DeliberationMessage]:
    """Convert database message records to DeliberationMessage objects."""
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


async def _get_similar_cases(session_data: dict[str, Any]) -> list[SimilarCase]:
    """Get similar cases for a session."""
    similar_case_ids = session_data.get("similar_case_ids") or []
    similar_cases = []

    for case_id in similar_case_ids[:5]:
        case_data = await db.get_case_by_id(str(case_id))
        if case_data:
            extraction = case_data.get("extraction_result", {}) or {}
            verdict = extraction.get("verdict", {}) or {}
            sentences = verdict.get("sentences", {}) or {}
            imprisonment = sentences.get("imprisonment", {}) or {}

            similar_cases.append(
                SimilarCase(
                    case_id=str(case_data.get("id", "")),
                    case_number=case_data.get("extraction_id", "Unknown"),
                    similarity_score=0.7,  # Default since we don't store this
                    similarity_reason="Retrieved from session",
                    verdict_summary=verdict.get("result", "Unknown"),
                    sentence_months=imprisonment.get("duration_months", 0) or 0,
                )
            )

    return similar_cases
