"""
Hash Verification Client Module
================================
This module provides a simple interface for other applications to register
documents with the Hash Verification system.

Usage:
------
    from hash_client import register_document

    # When user generates a document:
    result = register_document(
        hash_code="CM-A1B2C3D4E5F6",
        content_hash="sha256_of_pdf_content",
        user_id="your_app_name",
        client_name="Customer Name",
        document_type="carta_manifestacion",
        file_name="generated_document.pdf"
    )

    if result["success"]:
        print(f"Registered: {result['path']}")
"""

import json
import hashlib
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# ===============================================
# CONFIGURATION - Update this path for your setup
# ===============================================
# Option 1: Relative path (if all apps are in same parent directory)
# OUTPUT_DIR = Path(__file__).parent / "output"

# Option 2: Absolute path (recommended for production)
OUTPUT_DIR = Path("/Users/jimmy/Documents/GitHub/verificacion-hash/output")

# ===============================================
# Hash pattern validation
# ===============================================
HASH_PATTERN = re.compile(r'^[A-Z]{2}-[A-Z0-9]{12}$', re.IGNORECASE)


def generate_short_code(hash_code: str) -> str:
    """Generate a 6-character short code from the full hash."""
    if not HASH_PATTERN.match(hash_code.upper()):
        return ""
    hash_part = hash_code.upper().split('-')[1]
    return ''.join(hash_part[i] for i in range(0, 12, 2))


def register_document(
    hash_code: str,
    user_id: str,
    content_hash: Optional[str] = None,
    client_name: Optional[str] = None,
    document_type: Optional[str] = None,
    document_type_display: Optional[str] = None,
    file_name: Optional[str] = None,
    file_size: Optional[int] = None,
    form_data: Optional[Dict[str, Any]] = None,
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Register a document with the Hash Verification system.

    Args:
        hash_code: The document hash code (format: XX-XXXXXXXXXXXX)
        user_id: Identifier for the generating application
        content_hash: SHA-256 hash of the PDF content (optional)
        client_name: Name of the client/customer
        document_type: Internal type code (e.g., "carta_manifestacion")
        document_type_display: Display name for the type
        file_name: Original filename
        file_size: Size of the PDF in bytes
        form_data: Additional form data as dictionary
        overwrite: If True, overwrite existing registration

    Returns:
        Dict with keys: success, message, path (if successful)
    """
    # Validate hash format
    hash_code_upper = hash_code.strip().upper()
    if not HASH_PATTERN.match(hash_code_upper):
        return {
            "success": False,
            "message": f"Invalid hash format: {hash_code}. Expected: XX-XXXXXXXXXXXX"
        }

    # Sanitize user_id
    safe_user_id = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id.strip())
    if not safe_user_id:
        return {
            "success": False,
            "message": "user_id is required and cannot be empty"
        }

    # Create user directory
    user_dir = OUTPUT_DIR / safe_user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    # Generate trace_id and short_code
    trace_id = str(uuid.uuid4())
    short_code = generate_short_code(hash_code_upper)

    # Build metadata
    now = datetime.now()
    metadata = {
        "version": "1.0",
        "trace_id": trace_id,
        "hash_info": {
            "hash_code": hash_code_upper,
            "short_code": short_code,
            "algorithm": "SHA-256",
            "content_hash": content_hash or "",
            "metadata_hash": "",
            "combined_hash": "",
            "file_size": file_size or 0
        },
        "document_info": {
            "type": document_type or "",
            "type_display": document_type_display or "",
            "file_name": file_name or "",
            "creation_timestamp": now.strftime("%d/%m/%Y %H:%M:%S"),
            "creation_timestamp_iso": now.isoformat()
        },
        "user_info": {
            "user_id": safe_user_id,
            "client_name": client_name or ""
        },
        "form_data": form_data or {}
    }

    # Generate filename
    safe_hash = hash_code_upper.replace("-", "_")
    filename = f"metadata_{safe_hash}_{trace_id[:8]}.json"
    file_path = user_dir / filename

    # Check existing
    if file_path.exists() and not overwrite:
        # Check if same hash already registered for this user
        existing_files = list(user_dir.glob(f"metadata_{safe_hash}_*.json"))
        if existing_files:
            return {
                "success": False,
                "message": f"Hash {hash_code_upper} already registered for user {safe_user_id}"
            }

    # Write file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "message": "Document registered successfully",
            "path": str(file_path),
            "hash_code": hash_code_upper,
            "short_code": short_code
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to write file: {str(e)}"
        }


def calculate_pdf_hash(pdf_path: str) -> str:
    """Calculate SHA-256 hash of a PDF file."""
    with open(pdf_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def generate_hash_code(prefix: str = "OT") -> str:
    """
    Generate a new unique hash code.

    Args:
        prefix: 2-letter document type prefix (CM, IA, CE, IR, OT)

    Returns:
        Hash code in format XX-XXXXXXXXXXXX
    """
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=12))
    return f"{prefix.upper()}-{random_part}"


# ===============================================
# Example usage
# ===============================================
if __name__ == "__main__":
    # Test the registration
    result = register_document(
        hash_code="CM-EXAMPLE12345",
        user_id="test_app",
        content_hash="abc123def456",
        client_name="Test Client",
        document_type="carta_manifestacion",
        document_type_display="Carta de Manifestacion",
        file_name="test_document.pdf"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
