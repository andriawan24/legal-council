"""
Embedding module for generating vector embeddings of legal documents.

This module uses Vertex AI's text embedding model to generate embeddings
for extracted court decision data, enabling semantic search capabilities.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

from settings import get_settings

logger = logging.getLogger(__name__)

# Embedding model configuration
# gemini-embedding-001: up to 3072 dimensions, 2048 token max, excellent multilingual support
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768  # Can be configured up to 3072
MAX_BATCH_SIZE = 250  # Vertex AI batch limit
MAX_TEXT_LENGTH = 8000  # Characters, roughly ~2048 tokens for gemini-embedding-001


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""

    text: str
    embedding: list[float]
    token_count: int | None = None
    chunk_index: int | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class DocumentEmbeddings:
    """All embeddings for a single document."""

    decision_number: str
    extraction_embedding: EmbeddingResult | None = None
    summary_id_embedding: EmbeddingResult | None = None
    summary_en_embedding: EmbeddingResult | None = None
    chunk_embeddings: list[EmbeddingResult] | None = None
    metadata: dict[str, Any] | None = None


def _initialize_vertex_ai() -> None:
    """Initialize Vertex AI with project settings."""
    settings = get_settings()
    aiplatform.init(
        project=settings.gcp_project,
        location=settings.gcp_region,
    )


def _truncate_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """
    Truncate text to maximum length while trying to preserve complete sentences.

    Args:
        text: Text to truncate
        max_length: Maximum character length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    # Try to cut at sentence boundary
    truncated = text[:max_length]
    last_period = truncated.rfind(".")
    last_newline = truncated.rfind("\n")

    cut_point = max(last_period, last_newline)
    if cut_point > max_length * 0.7:  # Only use if we keep at least 70%
        return truncated[: cut_point + 1]

    return truncated


def _chunk_text(
    text: str,
    chunk_size: int = MAX_TEXT_LENGTH,
    overlap: int = 500,
) -> list[str]:
    """
    Split text into overlapping chunks for embedding.

    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            # Try to break at sentence or paragraph boundary
            chunk = text[start:end]
            last_period = chunk.rfind(".")
            last_newline = chunk.rfind("\n")

            break_point = max(last_period, last_newline)
            if break_point > chunk_size * 0.5:
                end = start + break_point + 1

        chunks.append(text[start:end].strip())
        start = end - overlap

        # Avoid tiny final chunks
        if len(text) - start < overlap:
            break

    return chunks


def extraction_to_text(extraction: dict[str, Any]) -> str:
    """
    Convert extraction result to searchable text representation.

    Creates a structured text format optimized for embedding and search.

    Args:
        extraction: Extraction result dictionary

    Returns:
        Text representation of the extraction
    """
    parts = []

    # Defendant information
    if defendant := extraction.get("defendant"):
        parts.append("TERDAKWA (DEFENDANT):")
        if name := defendant.get("name"):
            parts.append(f"Nama: {name}")
        if alias := defendant.get("alias"):
            parts.append(f"Alias: {alias}")
        if occupation := defendant.get("occupation"):
            parts.append(f"Pekerjaan: {occupation}")
        if address := defendant.get("address"):
            if full_addr := address.get("full_address"):
                parts.append(f"Alamat: {full_addr}")
            elif city := address.get("city"):
                parts.append(f"Kota: {city}")

    # Court information
    if court := extraction.get("court"):
        parts.append("\nPENGADILAN (COURT):")
        if court_name := court.get("court_name"):
            parts.append(f"Nama Pengadilan: {court_name}")
        if verdict_number := court.get("verdict_number"):
            parts.append(f"Nomor Putusan: {verdict_number}")

    # Indictment/charges
    if indictment := extraction.get("indictment"):
        parts.append("\nDAKWAAN (INDICTMENT):")
        if chronology := indictment.get("chronology"):
            parts.append(f"Kronologi: {chronology}")
        if crime_location := indictment.get("crime_location"):
            parts.append(f"Lokasi Kejadian: {crime_location}")
        if cited_articles := indictment.get("cited_articles"):
            articles_text = ", ".join(
                a.get("full_citation", a.get("article", ""))
                for a in cited_articles
                if a
            )
            if articles_text:
                parts.append(f"Pasal yang Didakwakan: {articles_text}")

    # Prosecution demand
    if prosecution := extraction.get("prosecution_demand"):
        parts.append("\nTUNTUTAN (PROSECUTION DEMAND):")
        if content := prosecution.get("content"):
            parts.append(f"Isi Tuntutan: {content}")
        if prison := prosecution.get("prison_sentence_description"):
            parts.append(f"Tuntutan Penjara: {prison}")

    # Legal facts
    if legal_facts := extraction.get("legal_facts"):
        parts.append("\nFAKTA HUKUM (LEGAL FACTS):")
        for category, facts in legal_facts.items():
            if facts and isinstance(facts, list):
                parts.append(f"{category}:")
                for fact in facts[:5]:  # Limit to avoid too long text
                    parts.append(f"  - {fact}")

    # Verdict
    if verdict := extraction.get("verdict"):
        parts.append("\nPUTUSAN (VERDICT):")
        if result := verdict.get("result"):
            parts.append(f"Hasil: {result}")
        if verdict_date := verdict.get("date"):
            parts.append(f"Tanggal: {verdict_date}")
        if sentences := verdict.get("sentences"):
            if imprisonment := sentences.get("imprisonment"):
                if desc := imprisonment.get("description"):
                    parts.append(f"Hukuman Penjara: {desc}")
            if fine := sentences.get("fine"):
                if amount := fine.get("amount"):
                    parts.append(f"Denda: Rp {amount:,.0f}")

    # State loss
    if state_loss := extraction.get("state_loss"):
        parts.append("\nKERUGIAN NEGARA (STATE LOSS):")
        if proven := state_loss.get("proven_amount"):
            parts.append(f"Kerugian Terbukti: Rp {proven:,.0f}")
        if returned := state_loss.get("returned_amount"):
            parts.append(f"Sudah Dikembalikan: Rp {returned:,.0f}")

    # Case metadata
    if metadata := extraction.get("case_metadata"):
        if category := metadata.get("crime_category"):
            parts.append(f"\nKategori Tindak Pidana: {category}")
        if institution := metadata.get("institution_involved"):
            parts.append(f"Instansi Terlibat: {institution}")

    return "\n".join(parts)


async def generate_embedding(
    text: str,
    task_type: str = "RETRIEVAL_DOCUMENT",
    title: str | None = None,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> EmbeddingResult:
    """
    Generate embedding for a single text.

    Args:
        text: Text to embed
        task_type: Type of embedding task (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, etc.)
        title: Optional title for the document
        model_name: Embedding model to use

    Returns:
        EmbeddingResult with embedding vector
    """
    _initialize_vertex_ai()

    # Truncate if too long
    truncated_text = _truncate_text(text)

    logger.debug(f"Generating embedding for text of length {len(truncated_text)}")

    try:
        model = TextEmbeddingModel.from_pretrained(model_name)

        # Create embedding input
        if title:
            embedding_input = TextEmbeddingInput(
                text=truncated_text,
                task_type=task_type,
                title=title,
            )
        else:
            embedding_input = TextEmbeddingInput(
                text=truncated_text,
                task_type=task_type,
            )

        # Generate embedding (run in executor since it's sync)
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: model.get_embeddings([embedding_input]),
        )

        embedding = embeddings[0]

        return EmbeddingResult(
            text=truncated_text,
            embedding=embedding.values,
            token_count=getattr(embedding, "token_count", None),
        )

    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise


async def generate_embeddings_batch(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> list[EmbeddingResult]:
    """
    Generate embeddings for multiple texts in batch.

    Args:
        texts: List of texts to embed
        task_type: Type of embedding task
        model_name: Embedding model to use

    Returns:
        List of EmbeddingResults
    """
    _initialize_vertex_ai()

    if not texts:
        return []

    # Truncate texts
    truncated_texts = [_truncate_text(t) for t in texts]

    logger.info(f"Generating embeddings for {len(truncated_texts)} texts")

    try:
        model = TextEmbeddingModel.from_pretrained(model_name)

        results = []

        # Process in batches
        for i in range(0, len(truncated_texts), MAX_BATCH_SIZE):
            batch = truncated_texts[i : i + MAX_BATCH_SIZE]

            embedding_inputs = [
                TextEmbeddingInput(text=t, task_type=task_type) for t in batch
            ]

            # Generate embeddings
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda inputs=embedding_inputs: model.get_embeddings(inputs),
            )

            for j, embedding in enumerate(embeddings):
                results.append(
                    EmbeddingResult(
                        text=batch[j],
                        embedding=embedding.values,
                        token_count=getattr(embedding, "token_count", None),
                        chunk_index=i + j,
                    )
                )

        logger.info(f"Generated {len(results)} embeddings")
        return results

    except Exception as e:
        logger.error(f"Failed to generate batch embeddings: {e}")
        raise


async def generate_query_embedding(
    query: str,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> list[float]:
    """
    Generate embedding for a search query.

    Uses RETRIEVAL_QUERY task type optimized for semantic search queries.

    Args:
        query: Search query text
        model_name: Embedding model to use

    Returns:
        Embedding vector as list of floats
    """
    result = await generate_embedding(
        text=query,
        task_type="RETRIEVAL_QUERY",
        model_name=model_name,
    )
    return result.embedding


async def embed_document(
    decision_number: str,
    extraction: dict[str, Any],
    summary_id: str | None = None,
    summary_en: str | None = None,
    include_chunks: bool = False,
) -> DocumentEmbeddings:
    """
    Generate all embeddings for a legal document.

    Creates embeddings for:
    - The extraction result (structured data as text)
    - Indonesian summary
    - English summary
    - Optionally, chunked embeddings for long documents

    Args:
        decision_number: Court decision number
        extraction: Extraction result dictionary
        summary_id: Indonesian summary text
        summary_en: English summary text
        include_chunks: Whether to create chunked embeddings

    Returns:
        DocumentEmbeddings containing all embeddings
    """
    logger.info(f"Generating embeddings for document: {decision_number}")

    doc_embeddings = DocumentEmbeddings(
        decision_number=decision_number,
        metadata={
            "extraction_confidence": extraction.get("extraction_confidence"),
        },
    )

    try:
        # Convert extraction to searchable text
        extraction_text = extraction_to_text(extraction)

        # Generate extraction embedding
        logger.debug("Generating extraction embedding...")
        doc_embeddings.extraction_embedding = await generate_embedding(
            text=extraction_text,
            task_type="RETRIEVAL_DOCUMENT",
            title=f"Court Decision {decision_number}",
        )

        # Generate summary embeddings
        if summary_id:
            logger.debug("Generating Indonesian summary embedding...")
            doc_embeddings.summary_id_embedding = await generate_embedding(
                text=summary_id,
                task_type="RETRIEVAL_DOCUMENT",
                title=f"Ringkasan Putusan {decision_number}",
            )

        if summary_en:
            logger.debug("Generating English summary embedding...")
            doc_embeddings.summary_en_embedding = await generate_embedding(
                text=summary_en,
                task_type="RETRIEVAL_DOCUMENT",
                title=f"Summary of Decision {decision_number}",
            )

        # Generate chunk embeddings for long documents
        if include_chunks and len(extraction_text) > MAX_TEXT_LENGTH:
            logger.debug("Generating chunk embeddings...")
            chunks = _chunk_text(extraction_text)
            chunk_results = await generate_embeddings_batch(
                texts=chunks,
                task_type="RETRIEVAL_DOCUMENT",
            )
            doc_embeddings.chunk_embeddings = chunk_results

        logger.info(
            f"Generated embeddings for {decision_number}: "
            f"extraction={doc_embeddings.extraction_embedding is not None}, "
            f"summary_id={doc_embeddings.summary_id_embedding is not None}, "
            f"summary_en={doc_embeddings.summary_en_embedding is not None}, "
            f"chunks={len(doc_embeddings.chunk_embeddings or [])}"
        )

        return doc_embeddings

    except Exception as e:
        logger.error(f"Failed to generate embeddings for {decision_number}: {e}")
        raise


def embeddings_to_dict(doc_embeddings: DocumentEmbeddings) -> dict[str, Any]:
    """
    Convert DocumentEmbeddings to a dictionary for storage/serialization.

    Args:
        doc_embeddings: DocumentEmbeddings instance

    Returns:
        Dictionary representation
    """
    result = {
        "decision_number": doc_embeddings.decision_number,
        "metadata": doc_embeddings.metadata,
    }

    if doc_embeddings.extraction_embedding:
        result["extraction"] = {
            "embedding": doc_embeddings.extraction_embedding.embedding,
            "text_preview": doc_embeddings.extraction_embedding.text[:500],
            "token_count": doc_embeddings.extraction_embedding.token_count,
        }

    if doc_embeddings.summary_id_embedding:
        result["summary_id"] = {
            "embedding": doc_embeddings.summary_id_embedding.embedding,
            "text": doc_embeddings.summary_id_embedding.text,
            "token_count": doc_embeddings.summary_id_embedding.token_count,
        }

    if doc_embeddings.summary_en_embedding:
        result["summary_en"] = {
            "embedding": doc_embeddings.summary_en_embedding.embedding,
            "text": doc_embeddings.summary_en_embedding.text,
            "token_count": doc_embeddings.summary_en_embedding.token_count,
        }

    if doc_embeddings.chunk_embeddings:
        result["chunks"] = [
            {
                "chunk_index": chunk.chunk_index,
                "embedding": chunk.embedding,
                "text_preview": chunk.text[:200],
                "token_count": chunk.token_count,
            }
            for chunk in doc_embeddings.chunk_embeddings
        ]

    return result
