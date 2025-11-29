"""
Services for Legal Council API.

Business logic and external service integrations.
"""

from services.embeddings import EmbeddingService
from services.case_parser import CaseParserService
from services.opinion_generator import OpinionGeneratorService

__all__ = [
    "EmbeddingService",
    "CaseParserService",
    "OpinionGeneratorService",
]
