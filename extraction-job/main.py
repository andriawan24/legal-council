"""
Cloud Function entry point for PDF extraction pipeline.

This module handles Cloud Storage events triggered when new PDFs are uploaded,
processes them through the LLM-based extraction pipeline, and stores results.
"""

import asyncio
import logging
import os
import traceback

import functions_framework
from google.cloud import storage

from database import insert_extraction, ExtractionStatus
from embeddings import embed_document, embeddings_to_dict
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
    """
    Extract decision number from file name.

    Expected format: {decision_number}.pdf or path/to/{decision_number}.pdf

    Args:
        file_name: The GCS object name

    Returns:
        Extracted decision number
    """
    # Get base name without path and extension
    base_name = os.path.basename(file_name)
    if base_name.lower().endswith(".pdf"):
        base_name = base_name[:-4]
    return base_name


async def _process_pdf_async(bucket_name: str, file_name: str) -> dict:
    """
    Async implementation of PDF processing pipeline.

    Args:
        bucket_name: GCS bucket name
        file_name: GCS object name (path to PDF)

    Returns:
        Dictionary containing extraction results and metadata
    """
    gcs_uri = f"gs://{bucket_name}/{file_name}"
    decision_number = _extract_decision_number(file_name)

    logger.info(f"Starting extraction for decision: {decision_number}")
    logger.info(f"Source: {gcs_uri}")

    temp_pdf_path = None

    try:
        # Download PDF to temporary file
        logger.info("Downloading PDF from GCS...")
        temp_pdf_path = await download_pdf_to_temp_file_gcs(bucket_name, file_name)
        logger.info(f"PDF downloaded to: {temp_pdf_path}")

        # Run extraction pipeline
        logger.info("Running PDF extraction pipeline...")
        extraction_result, summary_id, summary_en = await process_document_pdf_extraction(
            decision_number=decision_number,
            pdf_path=temp_pdf_path,
        )

        # Log extraction summary
        extraction_data = extraction_result.model_dump()
        non_null_fields = sum(
            1 for v in extraction_data.values() if v is not None
        )
        logger.info(
            f"Extraction completed for {decision_number}: "
            f"{non_null_fields} fields extracted, "
            f"confidence: {extraction_result.extraction_confidence}"
        )

        # Prepare result
        result = {
            "decision_number": decision_number,
            "source_uri": gcs_uri,
            "extraction": extraction_data,
            "summary_id": summary_id,
            "summary_en": summary_en,
            "status": "success",
        }

        # Generate embeddings if enabled
        settings = get_settings()
        doc_embeddings = None
        extraction_embedding = None
        summary_embedding = None

        if settings.enable_embeddings:
            logger.info("Generating document embeddings...")
            try:
                doc_embeddings = await embed_document(
                    decision_number=decision_number,
                    extraction=extraction_data,
                    summary_id=summary_id,
                    summary_en=summary_en,
                    include_chunks=settings.enable_chunk_embeddings,
                )
                result["embeddings"] = embeddings_to_dict(doc_embeddings)
                logger.info(f"Embeddings generated for {decision_number}")

                # Extract embedding vectors for database storage
                if doc_embeddings.extraction_embedding:
                    extraction_embedding = doc_embeddings.extraction_embedding.embedding
                if doc_embeddings.summary_en_embedding:
                    summary_embedding = doc_embeddings.summary_en_embedding.embedding

            except Exception as e:
                # Log but don't fail the whole pipeline if embeddings fail
                logger.warning(f"Failed to generate embeddings: {e}")
                result["embeddings_error"] = str(e)

        # Store in database if enabled and configured
        if settings.enable_database_storage and settings.database_url:
            logger.info("Storing extraction results in database...")
            try:
                # Insert extraction with JSONB data and embeddings
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

                result["database_id"] = db_record_id
                logger.info(f"Stored extraction {decision_number} in database with ID {db_record_id}")

            except Exception as e:
                # Log but don't fail the whole pipeline if database storage fails
                logger.warning(f"Failed to store in database: {e}")
                result["database_error"] = str(e)
        elif settings.enable_database_storage and not settings.database_url:
            logger.warning("Database storage enabled but DATABASE_URL not configured")

        return result

    except Exception as e:
        logger.error(f"Extraction failed for {decision_number}: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")

        # Store failed extraction in database for tracking
        settings = get_settings()
        if settings.enable_database_storage and settings.database_url:
            try:
                await insert_extraction(
                    extraction_id=None,  # May not have extracted decision number
                    extraction_result=None,
                    confidence=None,
                    status=ExtractionStatus.FAILED,
                    error_message=str(e),
                    source_file=file_name,
                )
                logger.info(f"Stored failed extraction record for {file_name}")
            except Exception as db_error:
                logger.warning(f"Failed to store error record: {db_error}")

        return {
            "decision_number": decision_number,
            "source_uri": gcs_uri,
            "status": "error",
            "error": str(e),
        }

    finally:
        # Cleanup temporary file
        if temp_pdf_path:
            cleanup_temp_file(temp_pdf_path)


async def download_pdf_to_temp_file_gcs(bucket_name: str, blob_name: str) -> str:
    """
    Download PDF from GCS to a temporary file.

    Args:
        bucket_name: GCS bucket name
        blob_name: GCS blob name (object path)

    Returns:
        Path to temporary file containing the PDF
    """
    import tempfile

    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_path = temp_file.name
    temp_file.close()

    try:
        # Download from GCS
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.download_to_filename(temp_path)
        logger.info(f"Downloaded gs://{bucket_name}/{blob_name} to {temp_path}")
        return temp_path
    except Exception as e:
        # Cleanup on failure
        cleanup_temp_file(temp_path)
        raise ValueError(f"Failed to download from GCS: {e}") from e


@functions_framework.cloud_event
def process_pdf_event(cloud_event):
    """
    Cloud Function entry point for processing PDF upload events.

    Triggered by Cloud Storage events when a new PDF is uploaded.
    Processes the PDF through the LLM extraction pipeline.

    Args:
        cloud_event: CloudEvent containing bucket and file information
    """
    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]

    # Skip non-PDF files
    if not file_name.lower().endswith(".pdf"):
        logger.info(f"Skipping non-PDF file: {file_name}")
        return {"status": "skipped", "reason": "not a PDF file"}

    logger.info(f"Processing PDF: gs://{bucket_name}/{file_name}")

    # Run async processing
    result = asyncio.run(_process_pdf_async(bucket_name, file_name))

    # Log result
    if result.get("status") == "success":
        logger.info(f"Successfully processed: {result.get('decision_number')}")
    else:
        logger.error(
            f"Failed to process: {result.get('decision_number')} - "
            f"{result.get('error')}"
        )

    return result


# HTTP endpoint for manual testing/triggering
@functions_framework.http
def process_pdf_http(request):
    """
    HTTP endpoint for manually triggering PDF extraction.

    Expected JSON body:
    {
        "bucket": "bucket-name",
        "name": "path/to/file.pdf"
    }

    Args:
        request: Flask request object

    Returns:
        JSON response with extraction results
    """
    try:
        request_json = request.get_json(silent=True)

        if not request_json:
            return {"error": "Request body must be JSON"}, 400

        bucket_name = request_json.get("bucket")
        file_name = request_json.get("name")

        if not bucket_name or not file_name:
            return {"error": "Missing 'bucket' or 'name' in request body"}, 400

        if not file_name.lower().endswith(".pdf"):
            return {"error": "File must be a PDF"}, 400

        logger.info(f"HTTP request to process: gs://{bucket_name}/{file_name}")

        # Run async processing
        result = asyncio.run(_process_pdf_async(bucket_name, file_name))

        status_code = 200 if result.get("status") == "success" else 500
        return result, status_code

    except Exception as e:
        logger.error(f"HTTP handler error: {e}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}, 500
