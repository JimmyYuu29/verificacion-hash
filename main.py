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

# Hash code patterns
# Full hash: XX-XXXXXXXXXXXX (2 letters, dash, 12 alphanumeric)
HASH_PATTERN = re.compile(r'^[A-Z]{2}-[A-Z0-9]{12}$', re.IGNORECASE)
# Short code (codigo hash comprimido): 6 alphanumeric characters
SHORT_CODE_PATTERN = re.compile(r'^[A-Z0-9]{6}$', re.IGNORECASE)

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


class HashInfoInput(BaseModel):
    hash_code: str
    short_code: Optional[str] = None
    algorithm: Optional[str] = "SHA-256"
    content_hash: Optional[str] = None
    metadata_hash: Optional[str] = None
    combined_hash: Optional[str] = None
    file_size: Optional[int] = None


class DocumentInfoInput(BaseModel):
    type: Optional[str] = None
    type_display: Optional[str] = None
    file_name: Optional[str] = None
    creation_timestamp: Optional[str] = None
    creation_timestamp_iso: Optional[str] = None


class UserInfoInput(BaseModel):
    user_id: str
    client_name: Optional[str] = None


class DocumentRegistration(BaseModel):
    version: Optional[str] = "1.0"
    trace_id: Optional[str] = None
    hash_info: HashInfoInput
    document_info: Optional[DocumentInfoInput] = None
    user_info: UserInfoInput
    form_data: Optional[Dict[str, Any]] = None


class RegistrationResult(BaseModel):
    success: bool
    message: str
    path: Optional[str] = None


# Core functions
def validate_hash_format(hash_code: str) -> bool:
    """Validate full hash code format (XX-XXXXXXXXXXXX)."""
    return bool(HASH_PATTERN.match(hash_code.upper()))


def validate_short_code_format(short_code: str) -> bool:
    """Validate compressed short code format (6 alphanumeric characters)."""
    return bool(SHORT_CODE_PATTERN.match(short_code.upper()))


def generate_short_code(hash_code: str) -> str:
    """
    Generate a compressed short code from a full hash code.

    Takes every other character from the 12-character hash portion.
    Example: CM-A1B2C3D4E5F6 -> A1B2C3 (positions 0,2,4,6,8,10 of the 12-char part)

    Args:
        hash_code: Full hash code (format: XX-XXXXXXXXXXXX)

    Returns:
        6-character short code
    """
    if not validate_hash_format(hash_code):
        return ""

    # Extract the 12-character portion after the prefix
    hash_part = hash_code.upper().split('-')[1]

    # Take characters at even positions (0, 2, 4, 6, 8, 10)
    short_code = ''.join(hash_part[i] for i in range(0, 12, 2))

    return short_code


def is_short_code(code: str) -> bool:
    """Check if the provided code is a short code (not a full hash)."""
    return validate_short_code_format(code) and not validate_hash_format(code)


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


def search_by_short_code(short_code: str, output_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Search for document metadata by compressed short code.

    The short code is generated from the full hash code by taking every other character
    from the 12-character hash portion.

    Args:
        short_code: The 6-character short code to search for
        output_dir: Path to the output directory containing user folders

    Returns:
        Metadata dictionary if found, None otherwise
    """
    short_code_upper = short_code.upper()

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

                # Check if stored short_code matches
                stored_short_code = metadata.get("hash_info", {}).get("short_code", "")
                if stored_short_code.upper() == short_code_upper:
                    return metadata

                # If no stored short_code, generate one from the full hash
                if stored_hash and not stored_short_code:
                    generated_short = generate_short_code(stored_hash)
                    if generated_short.upper() == short_code_upper:
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
                # Generate short code if not present
                short_code = metadata.get("hash_info", {}).get("short_code", "")
                if not short_code and stored_hash:
                    short_code = generate_short_code(stored_hash)

                # Check if partial matches full hash or short code
                if partial_upper in stored_hash.upper() or partial_upper in short_code.upper():
                    results.append({
                        "hash_code": stored_hash,
                        "short_code": short_code,
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

                # Get or generate short code
                hash_code = metadata.get("hash_info", {}).get("hash_code", "Unknown")
                short_code = metadata.get("hash_info", {}).get("short_code", "")
                if not short_code and hash_code != "Unknown":
                    short_code = generate_short_code(hash_code)

                # Collect for recent documents
                all_documents.append({
                    "hash_code": hash_code,
                    "short_code": short_code,
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

    Supports two formats:
    - **Full hash**: XX-XXXXXXXXXXXX (e.g., CM-A1B2C3D4E5F6)
    - **Short code (codigo comprimido)**: 6 alphanumeric characters (e.g., ABCD12)
    """
    code_upper = hash_code.strip().upper()
    metadata = None
    code_type = "full"

    # Check if it's a full hash format
    if validate_hash_format(code_upper):
        metadata = search_by_hash(code_upper, OUTPUT_DIR)
        code_type = "full"
    # Check if it's a short code format
    elif validate_short_code_format(code_upper):
        metadata = search_by_short_code(code_upper, OUTPUT_DIR)
        code_type = "short"
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid code format. Expected formats: XX-XXXXXXXXXXXX (full hash) or XXXXXX (6-character short code)"
        )

    if not metadata:
        if code_type == "short":
            raise HTTPException(
                status_code=404,
                detail=f"Short code '{code_upper}' not found in database"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Hash code '{code_upper}' not found in database"
            )

    # Add short_code to response if not already present
    if "hash_info" in metadata and "short_code" not in metadata["hash_info"]:
        full_hash = metadata["hash_info"].get("hash_code", "")
        if full_hash:
            metadata["hash_info"]["short_code"] = generate_short_code(full_hash)

    return VerificationResult(
        success=True,
        message="Document found and verified",
        metadata=metadata
    )


@app.post("/api/verify/integrity", response_model=IntegrityResult)
async def verify_integrity(
    hash_code: str = Query(..., description="The hash code or short code to verify"),
    file: UploadFile = File(..., description="PDF file to verify")
):
    """
    Verify document integrity by comparing uploaded PDF hash with stored hash.

    Supports two formats:
    - **Full hash**: XX-XXXXXXXXXXXX (e.g., CM-A1B2C3D4E5F6)
    - **Short code (codigo comprimido)**: 6 alphanumeric characters (e.g., ABCD12)

    - **file**: The PDF file to verify
    """
    code_upper = hash_code.strip().upper()

    # Validate format (accept both full hash and short code)
    if not validate_hash_format(code_upper) and not validate_short_code_format(code_upper):
        raise HTTPException(
            status_code=400,
            detail="Invalid code format. Expected formats: XX-XXXXXXXXXXXX (full hash) or XXXXXX (6-character short code)"
        )

    # Read file content
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file provided"
        )

    # Find the metadata first (using either format)
    if validate_hash_format(code_upper):
        metadata = search_by_hash(code_upper, OUTPUT_DIR)
    else:
        metadata = search_by_short_code(code_upper, OUTPUT_DIR)

    if not metadata:
        return IntegrityResult(
            valid=False,
            hash_code=code_upper,
            message="Code not found in database"
        )

    # Get the full hash code for the result
    full_hash_code = metadata.get("hash_info", {}).get("hash_code", code_upper)

    # Calculate hash of provided PDF
    calculated_hash = hashlib.sha256(content).hexdigest()
    stored_hash = metadata.get("hash_info", {}).get("content_hash", "")

    is_valid = calculated_hash.lower() == stored_hash.lower()

    return IntegrityResult(
        valid=is_valid,
        hash_code=full_hash_code,
        calculated_hash=calculated_hash,
        stored_hash=stored_hash,
        message="Document is authentic and unmodified" if is_valid else "Document has been modified or is not authentic"
    )


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


@app.post("/api/register", response_model=RegistrationResult)
async def register_document(registration: DocumentRegistration):
    """
    Register a new document by saving its metadata to the output directory.

    This endpoint allows remote applications to register verification documents
    without needing direct file system access.

    - **registration**: JSON body containing document metadata
    """
    # Validate hash format
    hash_code = registration.hash_info.hash_code.strip().upper()
    if not validate_hash_format(hash_code):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid hash_code format: {hash_code}. Expected format: XX-XXXXXXXXXXXX"
        )

    user_id = registration.user_info.user_id.strip()
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="user_id is required and cannot be empty"
        )

    # Sanitize user_id for filesystem safety (allow only alphanumeric, underscore, dash)
    safe_user_id = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id)

    # Create user directory if it doesn't exist
    user_dir = OUTPUT_DIR / safe_user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    # Generate short_code if not provided
    short_code = registration.hash_info.short_code
    if not short_code:
        short_code = generate_short_code(hash_code)

    # Generate trace_id if not provided
    trace_id = registration.trace_id
    if not trace_id:
        import uuid
        trace_id = str(uuid.uuid4())

    # Build the metadata dictionary
    metadata = {
        "version": registration.version or "1.0",
        "trace_id": trace_id,
        "hash_info": {
            "hash_code": hash_code,
            "short_code": short_code,
            "algorithm": registration.hash_info.algorithm or "SHA-256",
            "content_hash": registration.hash_info.content_hash or "",
            "metadata_hash": registration.hash_info.metadata_hash or "",
            "combined_hash": registration.hash_info.combined_hash or "",
            "file_size": registration.hash_info.file_size or 0
        },
        "document_info": {},
        "user_info": {
            "user_id": safe_user_id,
            "client_name": registration.user_info.client_name or ""
        },
        "form_data": registration.form_data or {}
    }

    # Add document_info if provided
    if registration.document_info:
        metadata["document_info"] = {
            "type": registration.document_info.type or "",
            "type_display": registration.document_info.type_display or "",
            "file_name": registration.document_info.file_name or "",
            "creation_timestamp": registration.document_info.creation_timestamp or "",
            "creation_timestamp_iso": registration.document_info.creation_timestamp_iso or datetime.now().isoformat()
        }
    else:
        metadata["document_info"] = {
            "type": "",
            "type_display": "",
            "file_name": "",
            "creation_timestamp": "",
            "creation_timestamp_iso": datetime.now().isoformat()
        }

    # Generate filename
    safe_hash = hash_code.replace("-", "_")
    filename = f"metadata_{safe_hash}_{trace_id[:8]}.json"
    file_path = user_dir / filename

    # Check if file already exists (optional: could allow overwrite)
    if file_path.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Document with hash {hash_code} already registered for user {safe_user_id}"
        )

    # Write the metadata file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except IOError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write metadata file: {str(e)}"
        )

    relative_path = str(file_path.relative_to(Path(".")))

    return RegistrationResult(
        success=True,
        message="Document registered successfully",
        path=relative_path
    )


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
