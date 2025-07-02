# app/core/utils.py
import hashlib
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
import unicodedata
from PIL import Image
import io
from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_unique_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())


def get_file_hash(file_path: Path) -> str:
    """
    Generate SHA256 hash of a file for duplicate detection.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hexadecimal hash string
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_image_hash(image_content: bytes) -> str:
    """
    Generate hash of image content for duplicate detection.
    
    Args:
        image_content: Raw image bytes
        
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(image_content).hexdigest()


def validate_image_file(filename: str, content_type: str, file_size: int) -> Dict[str, Any]:
    """
    Validate image file parameters.
    
    Args:
        filename: Original filename
        content_type: MIME type
        file_size: File size in bytes
        
    Returns:
        Dict with validation result and details
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Check file extension
    ext = Path(filename).suffix.lower()
    if ext not in settings.get_allowed_extensions_set():
        result["valid"] = False
        result["errors"].append(f"File extension '{ext}' not allowed. Allowed: {list(settings.get_allowed_extensions_set())}")
    
    # Check content type
    if not content_type or not content_type.startswith("image/"):
        result["valid"] = False
        result["errors"].append(f"Invalid content type: {content_type}")
    
    # Check file size
    if file_size <= 0:
        result["valid"] = False
        result["errors"].append("File is empty")
    elif file_size > settings.MAX_FILE_SIZE:
        result["valid"] = False
        result["errors"].append(f"File too large: {format_file_size(file_size)}. Max: {format_file_size(settings.MAX_FILE_SIZE)}")
    
    return result


def validate_image_file_upload(file: UploadFile) -> Dict[str, Any]:
    """
    Validate an uploaded image file object.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        Dict with validation result and details
    """
    return validate_image_file(
        filename=file.filename or "unknown",
        content_type=file.content_type or "",
        file_size=file.size or 0
    )


def validate_image_content(image_content: bytes) -> Dict[str, Any]:
    """
    Validate actual image content using PIL.
    
    Args:
        image_content: Raw image bytes
        
    Returns:
        Dict with validation result and image metadata
    """
    result = {
        "valid": True,
        "width": None,
        "height": None,
        "format": None,
        "errors": []
    }
    
    try:
        with Image.open(io.BytesIO(image_content)) as img:
            img.verify()  # Verify it's a valid image
            
        # Re-open to get metadata (verify() closes the image)
        with Image.open(io.BytesIO(image_content)) as img:
            result["width"], result["height"] = img.size
            result["format"] = img.format
            
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Invalid image content: {str(e)}")
    
    return result


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed_file"
    
    # Get just the filename part
    filename = os.path.basename(filename)
    
    # Replace problematic characters
    safe_chars = []
    for char in filename:
        if char.isalnum() or char in '.-_':
            safe_chars.append(char)
        else:
            safe_chars.append('_')
    
    result = ''.join(safe_chars)
    
    # Ensure it's not empty
    if not result or result in ['.', '..']:
        result = "sanitized_file"
    
    return result


def get_file_extension(filename: str) -> str:
    """
    Get file extension in lowercase.
    
    Args:
        filename: Name of the file
        
    Returns:
        File extension including the dot (e.g., '.jpg')
    """
    return Path(filename).suffix.lower()


def is_valid_image_extension(filename: str) -> bool:
    """
    Check if file has a valid image extension.
    
    Args:
        filename: Name of the file to validate
        
    Returns:
        True if extension is allowed, False otherwise
    """
    ext = get_file_extension(filename)
    return ext in settings.get_allowed_extensions_set()


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    try:
        return file_path.stat().st_size
    except Exception as e:
        logger.error(f"Failed to get size for file {file_path}: {e}")
        raise


def validate_file_size(file_size: int) -> bool:
    """
    Validate if file size is within allowed limits.
    
    Args:
        file_size: File size in bytes
        
    Returns:
        True if file size is acceptable, False otherwise
    """
    return 0 < file_size <= settings.MAX_FILE_SIZE


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def create_success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """
    Create standardized success response.
    
    Args:
        data: Response data
        message: Success message
        
    Returns:
        Formatted success response
    """
    return {
        "success": True,
        "message": message,
        "data": data
    }


def create_error_response(message: str, details: Optional[Dict] = None, error_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Create standardized error response.
    
    Args:
        message: Error message
        details: Additional error details
        error_code: Error code identifier
        
    Returns:
        Formatted error response
    """
    response = {
        "success": False,
        "message": message
    }
    
    if error_code:
        response["error_code"] = error_code
    
    if details:
        response["details"] = details
    
    return response


def create_validation_response(errors: List[str], warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Create standardized validation response.
    
    Args:
        errors: List of validation errors
        warnings: List of validation warnings
        
    Returns:
        Formatted validation response
    """
    response = {
        "valid": len(errors) == 0,
        "errors": errors
    }
    
    if warnings:
        response["warnings"] = warnings
    
    return response


def ensure_directory_exists(directory: Path) -> None:
    """
    Create directory if it doesn't exist.
    
    Args:
        directory: Path to directory
    """
    directory.mkdir(parents=True, exist_ok=True)


def get_unique_filename(base_filename: str, directory: Path) -> str:
    """
    Get a unique filename in the given directory.
    
    Args:
        base_filename: Desired filename
        directory: Target directory
        
    Returns:
        Unique filename
    """
    file_path = directory / base_filename
    
    if not file_path.exists():
        return base_filename
    
    # Add suffix to make unique
    stem = file_path.stem
    suffix = file_path.suffix
    counter = 1
    
    while file_path.exists():
        new_filename = f"{stem}_{counter}{suffix}"
        file_path = directory / new_filename
        counter += 1
    
    return file_path.name 