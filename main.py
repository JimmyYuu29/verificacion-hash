"""
Hash Verification Application - Backend API
Verifies document authenticity using hash codes from PDF footers.
"""

import json
import hashlib
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configuration
OUTPUT_DIR = Path("./output")

# Document type mapping
DOCUMENT_TYPES = {
    "CM": {"code": "carta_manifestacion", "display": "Carta de Manifestacion"},
    "IA": {"code": "informe_auditoria", "display": "Informe de Auditoria"},
    "CE": {"code": "carta_encargo", "display": "Carta de Encargo"},
    "IR": {"code": "informe_revision", "display": "Informe de Revision"},
    "OT": {"code": "otros", "display": "Otros Documentos"}
}

# Hash code pattern: XX-XXXXXXXXXXXX (2 letters, dash, 12 alphanumeric)
HASH_PATTERN = re.compile(r'^[A-Z]{2}-[A-Z0-9]{12}$', re.IGNORECASE)

app = FastAPI(
    title="Hash Verifier API",
    description="API for verifying document authenticity using hash codes",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class VerificationResult(BaseModel):
    success: bool
    message: str
    metadata: Optional[Dict[str, Any]] = None


class IntegrityResult(BaseModel):
    valid: bool
    hash_code: str
    calculated_hash: Optional[str] = None
    stored_hash: Optional[str] = None
    message: str


class StatsResult(BaseModel):
    total_documents: int
    by_type: Dict[str, int]
    by_user: Dict[str, int]
    recent_documents: List[Dict[str, Any]]


# Core functions
def validate_hash_format(hash_code: str) -> bool:
    """Validate hash code format."""
    return bool(HASH_PATTERN.match(hash_code.upper()))


def get_document_type(hash_code: str) -> Optional[Dict[str, str]]:
    """Get document type info from hash code prefix."""
    if len(hash_code) >= 2:
        prefix = hash_code[:2].upper()
        return DOCUMENT_TYPES.get(prefix)
    return None


def search_by_hash(hash_code: str, output_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Search for document metadata by hash code.

    Args:
        hash_code: The hash code to search for (e.g., "CM-A1B2C3D4E5F6")
        output_dir: Path to the output directory containing user folders

    Returns:
        Metadata dictionary if found, None otherwise
    """
    hash_code_upper = hash_code.upper()

    if not output_dir.exists():
        return None

    # Search through all user directories
    for user_dir in output_dir.iterdir():
        if not user_dir.is_dir():
            continue

        # Search through all metadata files in user directory
        for metadata_file in user_dir.glob("metadata_*.json"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                stored_hash = metadata.get("hash_info", {}).get("hash_code", "")
                if stored_hash.upper() == hash_code_upper:
                    return metadata
            except (json.JSONDecodeError, IOError):
                continue

    return None


def search_partial_hash(partial_hash: str, output_dir: Path, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for documents by partial hash match.

    Args:
        partial_hash: Partial hash string to search for
        output_dir: Path to the output directory
        limit: Maximum number of results to return

    Returns:
        List of matching metadata dictionaries
    """
    results = []
    partial_upper = partial_hash.upper()

    if not output_dir.exists():
        return results

    for user_dir in output_dir.iterdir():
        if not user_dir.is_dir():
            continue

        for metadata_file in user_dir.glob("metadata_*.json"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                stored_hash = metadata.get("hash_info", {}).get("hash_code", "")
                if partial_upper in stored_hash.upper():
                    results.append({
                        "hash_code": stored_hash,
                        "document_type": metadata.get("document_info", {}).get("type_display", "Unknown"),
                        "client_name": metadata.get("user_info", {}).get("client_name", "Unknown"),
                        "creation_date": metadata.get("document_info", {}).get("creation_timestamp", "Unknown")
                    })

                    if len(results) >= limit:
                        return results
            except (json.JSONDecodeError, IOError):
                continue

    return results


def verify_document_integrity(
    hash_code: str,
    pdf_content: bytes,
    output_dir: Path
) -> Dict[str, Any]:
    """
    Verify document integrity by comparing hashes.

    Args:
        hash_code: The hash code to verify
        pdf_content: Binary content of the PDF file
        output_dir: Path to the output directory

    Returns:
        Verification result dictionary
    """
    # Find the metadata
    metadata = search_by_hash(hash_code, output_dir)
    if not metadata:
        return {
            "valid": False,
            "hash_code": hash_code,
            "message": "Hash code not found in database"
        }

    # Calculate hash of provided PDF
    calculated_hash = hashlib.sha256(pdf_content).hexdigest()
    stored_hash = metadata.get("hash_info", {}).get("content_hash", "")

    is_valid = calculated_hash.lower() == stored_hash.lower()

    return {
        "valid": is_valid,
        "hash_code": hash_code,
        "calculated_hash": calculated_hash,
        "stored_hash": stored_hash,
        "message": "Document is authentic and unmodified" if is_valid else "Document has been modified or is not authentic"
    }


def get_statistics(output_dir: Path) -> Dict[str, Any]:
    """
    Get statistics about stored documents.

    Args:
        output_dir: Path to the output directory

    Returns:
        Statistics dictionary
    """
    stats = {
        "total_documents": 0,
        "by_type": {},
        "by_user": {},
        "recent_documents": []
    }

    all_documents = []

    if not output_dir.exists():
        return stats

    for user_dir in output_dir.iterdir():
        if not user_dir.is_dir():
            continue

        user_id = user_dir.name

        for metadata_file in user_dir.glob("metadata_*.json"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                stats["total_documents"] += 1

                # Count by type
                doc_type = metadata.get("document_info", {}).get("type_display", "Unknown")
                stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1

                # Count by user
                stats["by_user"][user_id] = stats["by_user"].get(user_id, 0) + 1

                # Collect for recent documents
                all_documents.append({
                    "hash_code": metadata.get("hash_info", {}).get("hash_code", "Unknown"),
                    "document_type": doc_type,
                    "client_name": metadata.get("user_info", {}).get("client_name", "Unknown"),
                    "creation_date": metadata.get("document_info", {}).get("creation_timestamp_iso", ""),
                    "user_id": user_id
                })
            except (json.JSONDecodeError, IOError):
                continue

    # Sort by creation date and get recent 5
    all_documents.sort(key=lambda x: x.get("creation_date", ""), reverse=True)
    stats["recent_documents"] = all_documents[:5]

    return stats


# API Endpoints
@app.get("/api/verify/{hash_code}", response_model=VerificationResult)
async def verify_hash(hash_code: str):
    """
    Verify a hash code and return document metadata.

    - **hash_code**: The hash code to verify (format: XX-XXXXXXXXXXXX)
    """
    # Validate format
    if not validate_hash_format(hash_code):
        raise HTTPException(
            status_code=400,
            detail="Invalid hash code format. Expected format: XX-XXXXXXXXXXXX (e.g., CM-A1B2C3D4E5F6)"
        )

    # Search for metadata
    metadata = search_by_hash(hash_code, OUTPUT_DIR)

    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=f"Hash code '{hash_code.upper()}' not found in database"
        )

    return VerificationResult(
        success=True,
        message="Document found and verified",
        metadata=metadata
    )


@app.post("/api/verify/integrity", response_model=IntegrityResult)
async def verify_integrity(
    hash_code: str = Query(..., description="The hash code to verify"),
    file: UploadFile = File(..., description="PDF file to verify")
):
    """
    Verify document integrity by comparing uploaded PDF hash with stored hash.

    - **hash_code**: The hash code to verify
    - **file**: The PDF file to verify
    """
    # Validate format
    if not validate_hash_format(hash_code):
        raise HTTPException(
            status_code=400,
            detail="Invalid hash code format"
        )

    # Read file content
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file provided"
        )

    # Verify integrity
    result = verify_document_integrity(hash_code, content, OUTPUT_DIR)

    return IntegrityResult(**result)


@app.get("/api/search")
async def search_documents(
    q: str = Query(..., min_length=3, description="Partial hash to search for")
):
    """
    Search for documents by partial hash match.

    - **q**: Partial hash string (minimum 3 characters)
    """
    results = search_partial_hash(q, OUTPUT_DIR)

    return {
        "success": True,
        "query": q,
        "count": len(results),
        "results": results
    }


@app.get("/api/stats", response_model=StatsResult)
async def get_stats():
    """
    Get statistics about stored documents.
    """
    stats = get_statistics(OUTPUT_DIR)
    return StatsResult(**stats)


@app.get("/api/document-types")
async def get_document_types():
    """
    Get available document types and their codes.
    """
    return {
        "success": True,
        "types": DOCUMENT_TYPES
    }


# Serve static files and HTML frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    html_path = Path("static/index.html")
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return HTMLResponse(content="<h1>Hash Verifier</h1><p>Frontend not found. Please check static/index.html</p>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
