"""
Database module for storing LLM extraction results and embeddings in Cloud SQL.

Uses asyncpg for async PostgreSQL access and pgvector for vector similarity search.
Schema: llm_extractions table with JSONB extraction_result and vector embeddings.
"""

import json
import logging
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any, AsyncIterator
from uuid import uuid4

import asyncpg
from asyncpg import Pool, Connection

from settings import get_settings

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Pool | None = None


class ExtractionStatus(str, Enum):
    """Status values for LLM extractions."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# Connection Management
# =============================================================================


async def get_pool() -> Pool:
    """
    Get or create the database connection pool.

    Returns:
        asyncpg connection pool
    """
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
    """
    Get a database connection from the pool.

    Usage:
        async with get_connection() as conn:
            await conn.execute(...)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


# =============================================================================
# Database Operations
# =============================================================================


def _format_vector(embedding: list[float] | None) -> str | None:
    """Format embedding list as pgvector string."""
    if embedding is None:
        return None
    return "[" + ",".join(str(x) for x in embedding) + "]"


async def insert_extraction(
    extraction_id: str | None,
    extraction_result: dict[str, Any] | None,
    confidence: float | None,
    summary_id: str | None = None,
    summary_en: str | None = None,
    extraction_embedding: list[float] | None = None,
    summary_embedding: list[float] | None = None,
    status: ExtractionStatus = ExtractionStatus.COMPLETED,
    error_message: str | None = None,
    source_file: str | None = None,
) -> str:
    """
    Insert an LLM extraction result into the database.

    Args:
        extraction_id: Decision number (can be NULL if extraction failed)
        extraction_result: Full extraction result as dict (JSONB)
        confidence: Extraction confidence score (0.0-1.0)
        summary_id: Indonesian summary text
        summary_en: English summary text
        extraction_embedding: Vector embedding of extraction
        summary_embedding: Vector embedding of summary
        status: Extraction status (default: completed)
        error_message: Error details if extraction failed
        source_file: Original filename for tracking

    Returns:
        The database record UUID
    """
    async with get_connection() as conn:
        extraction_vector = _format_vector(extraction_embedding)
        summary_vector = _format_vector(summary_embedding)

        # Check if extraction_id exists (only if not null)
        existing_id = None
        if extraction_id:
            existing_id = await conn.fetchval(
                "SELECT id FROM llm_extractions WHERE extraction_id = $1",
                extraction_id,
            )

        if existing_id:
            # Update existing record
            logger.info(f"Extraction {extraction_id} already exists, updating...")
            await conn.execute(
                """
                UPDATE llm_extractions SET
                    extraction_result = COALESCE($2, extraction_result),
                    extraction_confidence = COALESCE($3, extraction_confidence),
                    summary_id = COALESCE($4, summary_id),
                    summary_en = COALESCE($5, summary_en),
                    extraction_embedding = COALESCE($6::vector, extraction_embedding),
                    summary_embedding = COALESCE($7::vector, summary_embedding),
                    status = $8,
                    error_message = $9,
                    source_file = COALESCE($10, source_file),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
                """,
                existing_id,
                json.dumps(extraction_result) if extraction_result else None,
                confidence,
                summary_id,
                summary_en,
                extraction_vector,
                summary_vector,
                status.value,
                error_message,
                source_file,
            )
            logger.info(f"Updated extraction {extraction_id}")
            return str(existing_id)
        else:
            # Insert new record
            record_id = uuid4()
            await conn.execute(
                """
                INSERT INTO llm_extractions (
                    id, extraction_id, extraction_result,
                    extraction_confidence, summary_id, summary_en,
                    extraction_embedding, summary_embedding,
                    status, error_message, source_file
                ) VALUES (
                    $1, $2, $3,
                    $4, $5, $6,
                    $7::vector, $8::vector,
                    $9, $10, $11
                )
                """,
                record_id,
                extraction_id,
                json.dumps(extraction_result) if extraction_result else None,
                confidence,
                summary_id,
                summary_en,
                extraction_vector,
                summary_vector,
                status.value,
                error_message,
                source_file,
            )
            log_id = extraction_id or str(record_id)
            logger.info(f"Inserted extraction {log_id}")
            return str(record_id)


async def update_extraction_status(
    extraction_id: str,
    status: ExtractionStatus,
) -> bool:
    """
    Update the status of an extraction.

    Args:
        extraction_id: The extraction identifier
        status: New status value

    Returns:
        True if record was updated, False if not found
    """
    async with get_connection() as conn:
        result = await conn.execute(
            """
            UPDATE llm_extractions
            SET status = $2, updated_at = CURRENT_TIMESTAMP
            WHERE extraction_id = $1
            """,
            extraction_id,
            status.value,
        )
        updated = result.split()[-1] != "0"
        if updated:
            logger.info(f"Updated status for {extraction_id} to {status.value}")
        return updated


async def get_extraction(extraction_id: str) -> dict[str, Any] | None:
    """
    Get an extraction by extraction_id.

    Args:
        extraction_id: The extraction identifier

    Returns:
        Extraction record or None if not found
    """
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, extraction_id, extraction_result,
                   extraction_confidence, summary_id, summary_en,
                   status, error_message, source_file,
                   created_at, updated_at
            FROM llm_extractions
            WHERE extraction_id = $1
            """,
            extraction_id,
        )

        if row:
            result = dict(row)
            # Parse JSONB back to dict
            if result.get("extraction_result"):
                result["extraction_result"] = json.loads(result["extraction_result"])
            return result
        return None


async def get_extractions_by_status(
    status: ExtractionStatus,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Get extractions by status.

    Args:
        status: Status to filter by
        limit: Maximum results to return

    Returns:
        List of extraction records
    """
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id, extraction_id, extraction_result,
                   extraction_confidence, summary_id, summary_en,
                   status, error_message, source_file,
                   created_at, updated_at
            FROM llm_extractions
            WHERE status = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            status.value,
            limit,
        )

        results = []
        for row in rows:
            record = dict(row)
            if record.get("extraction_result"):
                record["extraction_result"] = json.loads(record["extraction_result"])
            results.append(record)
        return results


async def search_similar(
    query_embedding: list[float],
    limit: int = 10,
    min_similarity: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Search for similar extractions using vector similarity.

    Args:
        query_embedding: Query vector
        limit: Maximum results to return
        min_similarity: Minimum cosine similarity threshold

    Returns:
        List of similar extractions with similarity scores
    """
    async with get_connection() as conn:
        query_vector = _format_vector(query_embedding)

        results = await conn.fetch(
            """
            SELECT
                id, extraction_id, extraction_confidence,
                summary_en, status,
                1 - (extraction_embedding <=> $1::vector) as similarity
            FROM llm_extractions
            WHERE extraction_embedding IS NOT NULL
                AND status = 'completed'
                AND 1 - (extraction_embedding <=> $1::vector) >= $2
            ORDER BY extraction_embedding <=> $1::vector
            LIMIT $3
            """,
            query_vector,
            min_similarity,
            limit,
        )

        return [dict(row) for row in results]


async def search_similar_by_summary(
    query_embedding: list[float],
    limit: int = 10,
    min_similarity: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Search for similar extractions using summary embedding similarity.

    Args:
        query_embedding: Query vector
        limit: Maximum results to return
        min_similarity: Minimum cosine similarity threshold

    Returns:
        List of similar extractions with similarity scores
    """
    async with get_connection() as conn:
        query_vector = _format_vector(query_embedding)

        results = await conn.fetch(
            """
            SELECT
                id, extraction_id, extraction_confidence,
                summary_en, summary_id, status,
                1 - (summary_embedding <=> $1::vector) as similarity
            FROM llm_extractions
            WHERE summary_embedding IS NOT NULL
                AND status = 'completed'
                AND 1 - (summary_embedding <=> $1::vector) >= $2
            ORDER BY summary_embedding <=> $1::vector
            LIMIT $3
            """,
            query_vector,
            min_similarity,
            limit,
        )

        return [dict(row) for row in results]


async def check_health() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        True if connection is working
    """
    try:
        async with get_connection() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
