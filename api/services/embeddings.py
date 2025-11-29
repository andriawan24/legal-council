"""
Embedding Service for semantic search.

Generates text embeddings using Vertex AI for vector similarity search.
"""

import logging
from typing import Any

import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

from config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using Vertex AI."""

    def __init__(self):
        """Initialize the embedding service."""
        settings = get_settings()
        # Use us-central1 for text embedding models (most reliable availability)
        vertexai.init(project=settings.gcp_project, location="us-central1")
        self.model = TextEmbeddingModel.from_pretrained(settings.vertex_ai_embedding_model)
        self.dimension = settings.embedding_dimension

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate an embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        try:
            # Truncate text if too long
            max_length = 8000  # Approximate token limit
            if len(text) > max_length:
                text = text[:max_length]

            inputs = [TextEmbeddingInput(text=text, task_type="RETRIEVAL_QUERY")]
            embeddings = self.model.get_embeddings(
                inputs, output_dimensionality=self.dimension
            )

            if embeddings and len(embeddings) > 0:
                return embeddings[0].values

            logger.warning("No embedding returned from model")
            return []

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    async def generate_embeddings_batch(
        self, texts: list[str]
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            # Truncate and prepare inputs
            max_length = 8000
            inputs = [
                TextEmbeddingInput(
                    text=text[:max_length] if len(text) > max_length else text,
                    task_type="RETRIEVAL_DOCUMENT",
                )
                for text in texts
            ]

            embeddings = self.model.get_embeddings(
                inputs, output_dimensionality=self.dimension
            )
            return [emb.values for emb in embeddings]

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [[] for _ in texts]

    def build_search_text(self, case_data: dict[str, Any]) -> str:
        """
        Build searchable text from case data for embedding.

        Args:
            case_data: Parsed case information

        Returns:
            Concatenated text suitable for embedding
        """
        parts = []

        # Case type
        if case_data.get("case_type"):
            parts.append(f"Case type: {case_data['case_type']}")

        # Summary
        if case_data.get("summary"):
            parts.append(f"Summary: {case_data['summary']}")

        # Defendant profile
        defendant = case_data.get("defendant_profile", {})
        if defendant:
            if defendant.get("is_first_offender") is not None:
                status = "first offender" if defendant["is_first_offender"] else "repeat offender"
                parts.append(f"Defendant: {status}")
            if defendant.get("age"):
                parts.append(f"Age: {defendant['age']}")

        # Key facts
        if case_data.get("key_facts"):
            parts.append(f"Facts: {'. '.join(case_data['key_facts'][:5])}")

        # Charges
        if case_data.get("charges"):
            parts.append(f"Charges: {', '.join(case_data['charges'][:3])}")

        # Narcotics details
        narcotics = case_data.get("narcotics")
        if narcotics:
            parts.append(f"Substance: {narcotics.get('substance', 'unknown')}")
            parts.append(f"Weight: {narcotics.get('weight_grams', 0)} grams")
            parts.append(f"Intent: {narcotics.get('intent', 'unknown')}")

        # Corruption details
        corruption = case_data.get("corruption")
        if corruption:
            parts.append(f"State loss: {corruption.get('state_loss_idr', 0)} IDR")
            if corruption.get("position"):
                parts.append(f"Position: {corruption['position']}")

        return ". ".join(parts)


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
