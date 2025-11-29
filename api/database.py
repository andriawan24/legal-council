"""
Database module for Legal Council API.

Handles PostgreSQL connections with asyncpg and pgvector for semantic search.
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator
from uuid import uuid4, UUID

import asyncpg


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False


async def _lookup_case_uuids(
    conn, case_identifiers: list[str] | None
) -> list[str] | None:
    """
    Convert case identifiers to UUIDs by looking up in llm_extractions table.

    Case identifiers can be:
    - Already valid UUIDs
    - Case numbers like '456/PID.SUS/2019/PN.SBY' that need lookup
    """
    if not case_identifiers:
        return None

    valid_uuids = []
    for identifier in case_identifiers:
        if _is_valid_uuid(identifier):
            # Already a valid UUID
            valid_uuids.append(identifier)
        else:
            # Try to look up by case number (extraction_id)
            row = await conn.fetchrow(
                """
                SELECT id::text FROM llm_extractions
                WHERE extraction_id = $1
                LIMIT 1
                """,
                identifier,
            )
            if row:
                valid_uuids.append(row["id"])

    return valid_uuids if valid_uuids else None


from asyncpg import Connection, Pool

from config import get_settings

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Pool | None = None


# =============================================================================
# Connection Management
# =============================================================================


async def get_pool() -> Pool:
    """Get or create the database connection pool."""
    global _pool

    if _pool is None:
        settings = get_settings()

        if not settings.database_url:
            raise ValueError("DATABASE_URL is not configured")

        logger.info("Creating database connection pool...")

        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=settings.database_pool_min_size,
            max_size=settings.database_pool_max_size,
            command_timeout=settings.database_command_timeout,
        )

        logger.info("Database connection pool created")

    return _pool


async def close_pool() -> None:
    """Close the database connection pool."""
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


@asynccontextmanager
async def get_connection() -> AsyncIterator[Connection]:
    """Get a database connection from the pool."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


def _format_vector(embedding: list[float] | None) -> str | None:
    """Format embedding list as pgvector string."""
    if embedding is None:
        return None
    return "[" + ",".join(str(x) for x in embedding) + "]"


# =============================================================================
# Session Operations
# =============================================================================


async def create_session(
    user_id: str | None,
    case_input: dict[str, Any],
    similar_case_ids: list[str] | None = None,
) -> str:
    """Create a new deliberation session."""
    async with get_connection() as conn:
        session_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO deliberation_sessions (
                id, user_id, status, case_input, similar_case_ids,
                created_at, updated_at
            ) VALUES ($1, $2, 'active', $3, $4, NOW(), NOW())
            """,
            session_id,
            user_id,
            json.dumps(case_input),
            similar_case_ids,
        )
        logger.info(f"Created session {session_id}")
        return session_id


async def get_session(session_id: str) -> dict[str, Any] | None:
    """Get a session by ID."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id, status, case_input, similar_case_ids,
                   created_at, updated_at, concluded_at
            FROM deliberation_sessions
            WHERE id = $1
            """,
            session_id,
        )

        if row:
            result = dict(row)
            if result.get("case_input"):
                result["case_input"] = json.loads(result["case_input"])
            return result
        return None


async def list_sessions(
    user_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """List sessions with optional filters."""
    async with get_connection() as conn:
        conditions = []
        params = []
        param_count = 0

        if user_id:
            param_count += 1
            conditions.append(f"user_id = ${param_count}")
            params.append(user_id)

        if status and status != "all":
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM deliberation_sessions {where_clause}"
        total = await conn.fetchval(count_query, *params)

        # Get paginated results
        offset = (page - 1) * limit
        param_count += 1
        limit_param = param_count
        param_count += 1
        offset_param = param_count

        query = f"""
            SELECT id, user_id, status, case_input, similar_case_ids,
                   created_at, updated_at, concluded_at
            FROM deliberation_sessions
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        params.extend([limit, offset])

        rows = await conn.fetch(query, *params)

        results = []
        for row in rows:
            record = dict(row)
            if record.get("case_input"):
                record["case_input"] = json.loads(record["case_input"])
            results.append(record)

        return results, total


async def update_session_status(
    session_id: str,
    status: str,
) -> bool:
    """Update session status."""
    async with get_connection() as conn:
        concluded_at = "NOW()" if status == "concluded" else "NULL"
        result = await conn.execute(
            f"""
            UPDATE deliberation_sessions
            SET status = $2, updated_at = NOW(),
                concluded_at = {concluded_at}
            WHERE id = $1
            """,
            session_id,
            status,
        )
        return result.split()[-1] != "0"


async def delete_session(session_id: str) -> bool:
    """Archive (soft delete) a session."""
    return await update_session_status(session_id, "archived")


# =============================================================================
# Message Operations
# =============================================================================


async def create_message(
    session_id: str,
    sender_type: str,
    agent_id: str | None,
    content: str,
    intent: str | None = None,
    cited_case_ids: list[str] | None = None,
    cited_laws: list[str] | None = None,
) -> str:
    """Create a new deliberation message."""
    async with get_connection() as conn:
        # Convert case identifiers (case numbers or UUIDs) to actual UUIDs
        # by looking up in llm_extractions table
        valid_case_ids = await _lookup_case_uuids(conn, cited_case_ids)

        message_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO deliberation_messages (
                id, session_id, sender_type, agent_id, content,
                intent, cited_case_ids, cited_laws, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            """,
            message_id,
            session_id,
            sender_type,
            agent_id,
            content,
            intent,
            valid_case_ids,
            cited_laws,
        )

        # Update session timestamp
        await conn.execute(
            "UPDATE deliberation_sessions SET updated_at = NOW() WHERE id = $1",
            session_id,
        )

        return message_id


async def get_messages(
    session_id: str,
    limit: int = 50,
    before_id: str | None = None,
) -> list[dict[str, Any]]:
    """Get messages for a session."""
    async with get_connection() as conn:
        if before_id:
            query = """
                SELECT id, session_id, sender_type, agent_id, content,
                       intent, cited_case_ids, cited_laws, created_at
                FROM deliberation_messages
                WHERE session_id = $1
                  AND created_at < (
                      SELECT created_at FROM deliberation_messages WHERE id = $2
                  )
                ORDER BY created_at DESC
                LIMIT $3
            """
            rows = await conn.fetch(query, session_id, before_id, limit)
        else:
            query = """
                SELECT id, session_id, sender_type, agent_id, content,
                       intent, cited_case_ids, cited_laws, created_at
                FROM deliberation_messages
                WHERE session_id = $1
                ORDER BY created_at ASC
                LIMIT $2
            """
            rows = await conn.fetch(query, session_id, limit)

        return [dict(row) for row in rows]


# =============================================================================
# Legal Opinion Operations
# =============================================================================


async def save_legal_opinion(
    session_id: str,
    opinion_data: dict[str, Any],
) -> str:
    """Save a legal opinion for a session."""
    async with get_connection() as conn:
        opinion_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO legal_opinions (id, session_id, opinion_data, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (session_id)
            DO UPDATE SET opinion_data = $3, created_at = NOW()
            """,
            opinion_id,
            session_id,
            json.dumps(opinion_data, default=str),
        )
        return opinion_id


async def get_legal_opinion(session_id: str) -> dict[str, Any] | None:
    """Get the legal opinion for a session."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, session_id, opinion_data, created_at
            FROM legal_opinions
            WHERE session_id = $1
            """,
            session_id,
        )

        if row:
            result = dict(row)
            if result.get("opinion_data"):
                result["opinion_data"] = json.loads(result["opinion_data"])
            return result
        return None


# =============================================================================
# Case Operations (from llm_extractions table)
# =============================================================================


async def get_case_by_id(case_id: str) -> dict[str, Any] | None:
    """Get a case by its ID."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, extraction_id, extraction_result,
                   extraction_confidence, summary_en, summary_id,
                   status, source_file, created_at
            FROM llm_extractions
            WHERE id::text = $1 OR extraction_id = $1
            """,
            case_id,
        )

        if row:
            result = dict(row)
            if result.get("extraction_result"):
                result["extraction_result"] = json.loads(result["extraction_result"])
            return result
        return None


async def search_cases_by_text(
    query: str,
    filters: dict[str, Any] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search cases using text matching in JSONB."""
    async with get_connection() as conn:
        # Build filter conditions
        conditions = ["status = 'completed'"]
        params = [f"%{query}%", limit]

        base_query = """
            SELECT id, extraction_id, extraction_result,
                   extraction_confidence, summary_en, summary_id,
                   created_at
            FROM llm_extractions
            WHERE (
                summary_en ILIKE $1
                OR summary_id ILIKE $1
                OR extraction_result::text ILIKE $1
            )
        """

        # Add filter conditions
        if filters:
            if filters.get("case_type"):
                conditions.append(
                    "extraction_result->'case_metadata'->>'crime_category' ILIKE $"
                    + str(len(params) + 1)
                )
                params.append(f"%{filters['case_type']}%")

        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        base_query += " ORDER BY extraction_confidence DESC NULLS LAST LIMIT $2"

        rows = await conn.fetch(base_query, *params)

        results = []
        for row in rows:
            record = dict(row)
            if record.get("extraction_result"):
                record["extraction_result"] = json.loads(record["extraction_result"])
            results.append(record)

        return results


async def search_cases_by_vector(
    query_embedding: list[float],
    filters: dict[str, Any] | None = None,
    limit: int = 10,
    min_similarity: float = 0.5,
) -> list[dict[str, Any]]:
    """Search cases using vector similarity."""
    async with get_connection() as conn:
        query_vector = _format_vector(query_embedding)

        query = """
            SELECT
                id, extraction_id, extraction_result,
                extraction_confidence, summary_en, summary_id,
                created_at,
                1 - (summary_embedding <=> $1::vector) as similarity
            FROM llm_extractions
            WHERE summary_embedding IS NOT NULL
                AND status = 'completed'
                AND 1 - (summary_embedding <=> $1::vector) >= $2
            ORDER BY summary_embedding <=> $1::vector
            LIMIT $3
        """

        rows = await conn.fetch(query, query_vector, min_similarity, limit)

        results = []
        for row in rows:
            record = dict(row)
            if record.get("extraction_result"):
                record["extraction_result"] = json.loads(record["extraction_result"])
            results.append(record)

        return results


async def get_case_statistics(
    case_type: str | None = None,
    substance_type: str | None = None,
    weight_min: float | None = None,
    weight_max: float | None = None,
) -> dict[str, Any]:
    """Get case statistics with optional filters."""
    async with get_connection() as conn:
        conditions = ["status = 'completed'"]
        params = []

        if case_type:
            params.append(f"%{case_type}%")
            conditions.append(
                f"extraction_result->'case_metadata'->>'crime_category' ILIKE ${len(params)}"
            )

        where_clause = " AND ".join(conditions)

        # Get sentence statistics from verdict data
        query = f"""
            WITH case_sentences AS (
                SELECT
                    (extraction_result->'verdict'->'sentences'->>'duration_months')::int as sentence_months,
                    extraction_result->'verdict'->>'result' as verdict_result
                FROM llm_extractions
                WHERE {where_clause}
                  AND extraction_result->'verdict'->'sentences'->>'duration_months' IS NOT NULL
            )
            SELECT
                COUNT(*) as total_cases,
                MIN(sentence_months) as min_months,
                MAX(sentence_months) as max_months,
                AVG(sentence_months)::float as avg_months,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sentence_months)::float as median_months,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sentence_months)::float as p25,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sentence_months)::float as p75,
                COUNT(*) FILTER (WHERE verdict_result = 'guilty') as guilty_count,
                COUNT(*) FILTER (WHERE verdict_result = 'not_guilty') as not_guilty_count,
                COUNT(*) FILTER (WHERE verdict_result = 'acquitted') as acquitted_count
            FROM case_sentences
        """

        row = await conn.fetchrow(query, *params)

        if row and row["total_cases"] > 0:
            return {
                "total_cases": row["total_cases"],
                "sentence_distribution": {
                    "min_months": row["min_months"] or 0,
                    "max_months": row["max_months"] or 0,
                    "median_months": row["median_months"] or 0,
                    "average_months": round(row["avg_months"] or 0, 2),
                    "percentiles": {
                        "p25": row["p25"] or 0,
                        "p50": row["median_months"] or 0,
                        "p75": row["p75"] or 0,
                    },
                },
                "verdict_distribution": {
                    "guilty": row["guilty_count"] or 0,
                    "not_guilty": row["not_guilty_count"] or 0,
                    "rehabilitation": row["acquitted_count"] or 0,
                },
            }

        # Return default stats if no data
        return {
            "total_cases": 0,
            "sentence_distribution": {
                "min_months": 0,
                "max_months": 0,
                "median_months": 0,
                "average_months": 0,
                "percentiles": {"p25": 0, "p50": 0, "p75": 0},
            },
            "verdict_distribution": {
                "guilty": 0,
                "not_guilty": 0,
                "rehabilitation": 0,
            },
        }


# =============================================================================
# Health Check
# =============================================================================


async def check_health() -> bool:
    """Check database connection health."""
    try:
        async with get_connection() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
