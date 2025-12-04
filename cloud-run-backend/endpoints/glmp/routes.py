"""GLMP endpoints"""

from fastapi import APIRouter, HTTPException
from google.cloud import storage
import json

from utils.logging import structured_logger

router = APIRouter()

BUCKET_NAME = "regal-scholar-453620-r7-podcast-storage"
PREFIX = "glmp-v2/processes/"


@router.get("/api/glmp/processes")
async def list_glmp_processes():
    """List all available GLMP processes from Google Cloud Storage"""
    try:
        structured_logger.info("Listing GLMP processes",
                              bucket_name=BUCKET_NAME,
                              prefix=PREFIX)
        
        # Initialize GCS client
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs(prefix=PREFIX)
        
        processes = []
        for blob in blobs:
            if blob.name.endswith('.json'):
                # Extract process name from file path
                process_name = blob.name.replace(PREFIX, '').replace('.json', '')
                processes.append({
                    'id': process_name,
                    'name': process_name.replace('-', ' ').title(),
                    'file_path': blob.name,
                    'url': f"gs://{BUCKET_NAME}/{blob.name}",
                    'size': blob.size,
                    'updated': blob.updated.isoformat() if blob.updated else None
                })
        
        structured_logger.info("Found GLMP processes",
                              process_count=len(processes))
        return {"processes": processes, "count": len(processes)}
        
    except Exception as e:
        structured_logger.error("Error listing GLMP processes",
                               bucket_name=BUCKET_NAME,
                               prefix=PREFIX,
                               error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list GLMP processes: {str(e)}")


@router.get("/api/glmp/processes/{process_id}")
async def get_glmp_process(process_id: str):
    """Get a specific GLMP process flowchart from Google Cloud Storage"""
    try:
        file_path = f"{PREFIX}{process_id}.json"
        
        structured_logger.info("Fetching GLMP process",
                              process_id=process_id,
                              file_path=file_path)
        
        # Initialize GCS client
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_path)
        
        if not blob.exists():
            structured_logger.warning("GLMP process not found",
                                    process_id=process_id,
                                    file_path=file_path)
            raise HTTPException(status_code=404, detail=f"GLMP process '{process_id}' not found")
        
        # Download and parse JSON
        json_content = blob.download_as_text()
        process_data = json.loads(json_content)
        
        structured_logger.info("Loaded GLMP process",
                              process_id=process_id)
        
        # Extract key information
        mermaid_code = process_data.get('mermaid_syntax', '') or process_data.get('mermaid', '') or process_data.get('flowchart', '')
        
        return {
            "process_id": process_id,
            "data": process_data,
            "mermaid_code": mermaid_code,
            "metadata": {
                "title": process_data.get('title', process_data.get('name', process_id.replace('-', ' ').title())),
                "description": process_data.get('description', ''),
                "category": process_data.get('category', ''),
                "version": process_data.get('version', '1.0'),
                "authors": process_data.get('authors', []),
                "references": process_data.get('references', [])
            }
        }
        
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        structured_logger.error("Invalid JSON in GLMP process",
                               process_id=process_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail=f"Invalid JSON format in process file: {str(e)}")
    except Exception as e:
        structured_logger.error("Error fetching GLMP process",
                               process_id=process_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch GLMP process: {str(e)}")


@router.get("/api/glmp/processes/{process_id}/preview")
async def preview_glmp_process(process_id: str):
    """Get a lightweight preview of a GLMP process (metadata only)"""
    try:
        file_path = f"{PREFIX}{process_id}.json"
        
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_path)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail=f"GLMP process '{process_id}' not found")
        
        # Download and parse JSON
        json_content = blob.download_as_text()
        process_data = json.loads(json_content)
        
        # Return only metadata (no large mermaid code)
        return {
            "process_id": process_id,
            "title": process_data.get('title', process_data.get('name', process_id.replace('-', ' ').title())),
            "description": process_data.get('description', ''),
            "category": process_data.get('category', ''),
            "version": process_data.get('version', '1.0'),
            "has_mermaid": bool(process_data.get('mermaid_syntax') or process_data.get('mermaid') or process_data.get('flowchart')),
            "file_size": blob.size,
            "updated": blob.updated.isoformat() if blob.updated else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Error previewing GLMP process",
                               process_id=process_id,
                               error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to preview GLMP process: {str(e)}")

