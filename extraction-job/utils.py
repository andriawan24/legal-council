import json
import logging
from google.cloud import storage

logger = logging.getLogger(__name__)

class TruncationError(Exception):
    """Raised when LLM response is truncated."""
    pass

def _sanitize_json_control_chars(json_str: str) -> str:
    """Sanitize control characters in JSON string."""
    # Basic implementation - expanded as needed
    return json_str

async def generate_summary_id(data: dict) -> str:
    """Mock summary generator for Indonesian."""
    return "Ringkasan belum diimplementasikan."

async def generate_summary_en(data: dict) -> str:
    """Mock summary generator for English."""
    return "Summary not yet implemented."

def is_gcs_url(url: str) -> bool:
    """Check if URL is a GCS path."""
    return url.startswith("gs://")

async def download_from_gcs(uri: str, dest_path: str) -> None:
    """Download file from GCS."""
    try:
        # uri format: gs://bucket-name/path/to/object
        parts = uri.replace("gs://", "").split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid GCS URI: {uri}")
        
        bucket_name, blob_name = parts
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        blob.download_to_filename(dest_path)
        logger.info(f"Downloaded {uri} to {dest_path}")
    except Exception as e:
        logger.error(f"Failed to download from GCS: {e}")
        raise
