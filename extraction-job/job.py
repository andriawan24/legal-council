"""
Cloud Run Job entry point for batch PDF extraction.

This module processes PDFs from a GCS bucket in batch mode,
suitable for Cloud Run Jobs or scheduled processing.
"""

import asyncio
import logging
import os
import sys
from typing import Optional

from google.cloud import storage

from database import insert_extraction, ExtractionStatus, close_pool
from embeddings import embed_document
from pdf_extraction import (
    cleanup_temp_file,
    process_document_pdf_extraction,
)
from settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Google Cloud clients
storage_client = storage.Client()


def _extract_decision_number(file_name: str) -> str:
    """Extract decision number from file name."""
    base_name = os.path.basename(file_name)
    if base_name.lower().endswith(".pdf"):
        base_name = base_name[:-4]
    return base_name


async def download_pdf_to_temp(bucket_name: str, blob_name: str) -> str:
    """Download PDF from GCS to a temporary file."""
    import tempfile

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_path = temp_file.name
    temp_file.close()

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(temp_path)
        logger.info(f"Downloaded gs://{bucket_name}/{blob_name}")
        return temp_path
    except Exception as e:
        cleanup_temp_file(temp_path)
        raise ValueError(f"Failed to download from GCS: {e}") from e


async def process_single_pdf(bucket_name: str, file_name: str) -> dict:
    """Process a single PDF file."""
    settings = get_settings()
    gcs_uri = f"gs://{bucket_name}/{file_name}"
    decision_number = _extract_decision_number(file_name)
    temp_pdf_path = None

    logger.info(f"Processing: {gcs_uri}")

    try:
        # Download PDF
        temp_pdf_path = await download_pdf_to_temp(bucket_name, file_name)

        # Extract data using LLM
        extraction_result, summary_id, summary_en = await process_document_pdf_extraction(
            decision_number=decision_number,
            pdf_path=temp_pdf_path,
        )

        extraction_data = extraction_result.model_dump()

        # Generate embeddings
        extraction_embedding = None
        summary_embedding = None

        if settings.enable_embeddings:
            try:
                doc_embeddings = await embed_document(
                    decision_number=decision_number,
                    extraction=extraction_data,
                    summary_id=summary_id,
                    summary_en=summary_en,
                    include_chunks=settings.enable_chunk_embeddings,
                )
                if doc_embeddings.extraction_embedding:
                    extraction_embedding = doc_embeddings.extraction_embedding.embedding
                if doc_embeddings.summary_en_embedding:
                    summary_embedding = doc_embeddings.summary_en_embedding.embedding
                logger.info(f"Generated embeddings for {decision_number}")
            except Exception as e:
                logger.warning(f"Failed to generate embeddings: {e}")

        # Store in database
        if settings.enable_database_storage and settings.database_url:
            db_record_id = await insert_extraction(
                extraction_id=decision_number,
                extraction_result=extraction_data,
                confidence=extraction_result.extraction_confidence,
                summary_id=summary_id,
                summary_en=summary_en,
                extraction_embedding=extraction_embedding,
                summary_embedding=summary_embedding,
                source_file=file_name,
            )
            logger.info(f"Stored {decision_number} with ID {db_record_id}")

        return {"file": file_name, "status": "success", "decision_number": decision_number}

    except Exception as e:
        logger.error(f"Failed to process {file_name}: {e}")

        # Store failed record
        if settings.enable_database_storage and settings.database_url:
            try:
                await insert_extraction(
                    extraction_id=None,
                    extraction_result=None,
                    confidence=None,
                    status=ExtractionStatus.FAILED,
                    error_message=str(e),
                    source_file=file_name,
                )
            except Exception as db_error:
                logger.warning(f"Failed to store error record: {db_error}")

        return {"file": file_name, "status": "error", "error": str(e)}

    finally:
        if temp_pdf_path:
            cleanup_temp_file(temp_pdf_path)


async def process_bucket(
    bucket_name: str,
    prefix: Optional[str] = None,
    limit: Optional[int] = None,
) -> dict:
    """
    Process all PDFs in a GCS bucket.

    Args:
        bucket_name: GCS bucket name
        prefix: Optional prefix to filter files (e.g., "pending/")
        limit: Optional limit on number of files to process

    Returns:
        Summary of processing results
    """
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)

    pdf_files = [
        blob.name for blob in blobs
        if blob.name.lower().endswith(".pdf")
    ]

    if limit:
        pdf_files = pdf_files[:limit]

    logger.info(f"Found {len(pdf_files)} PDF files to process")

    results = {"success": 0, "failed": 0, "files": []}

    for file_name in pdf_files:
        result = await process_single_pdf(bucket_name, file_name)
        results["files"].append(result)

        if result["status"] == "success":
            results["success"] += 1
        else:
            results["failed"] += 1

    return results


async def main():
    """Main entry point for Cloud Run Job."""
    # Get configuration from environment variables
    bucket_name = os.environ.get("SOURCE_BUCKET")
    prefix = os.environ.get("SOURCE_PREFIX", "")
    limit = os.environ.get("PROCESS_LIMIT")
    single_file = os.environ.get("SINGLE_FILE")  # For processing a specific file

    if not bucket_name:
        logger.error("SOURCE_BUCKET environment variable is required")
        sys.exit(1)

    try:
        if single_file:
            # Process a single file
            logger.info(f"Processing single file: {single_file}")
            result = await process_single_pdf(bucket_name, single_file)
            success = result["status"] == "success"
        else:
            # Process all files in bucket
            logger.info(f"Processing bucket: gs://{bucket_name}/{prefix or ''}")
            results = await process_bucket(
                bucket_name=bucket_name,
                prefix=prefix if prefix else None,
                limit=int(limit) if limit else None,
            )

            logger.info(f"Processing complete: {results['success']} success, {results['failed']} failed")
            success = results["failed"] == 0

    finally:
        # Clean up database connections
        await close_pool()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
