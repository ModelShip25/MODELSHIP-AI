# app/models/image.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from pathlib import Path


class ImageMetadata(BaseModel):
    """Schema for uploaded image metadata."""
    id: str = Field(..., description="Unique image identifier")
    filename: str = Field(..., description="Original filename")
    stored_filename: str = Field(..., description="Sanitized stored filename")
    path: str = Field(..., description="Storage path")
    size_bytes: int = Field(..., description="File size in bytes", gt=0)
    size_formatted: str = Field(..., description="Human-readable file size")
    content_type: str = Field(..., description="MIME type")
    file_hash: str = Field(..., description="SHA256 hash for duplicate detection")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ImageUploadResponse(BaseModel):
    """Response schema for single image upload."""
    success: bool = Field(True, description="Upload success status")
    message: str = Field("Image uploaded successfully", description="Response message")
    data: ImageMetadata = Field(..., description="Uploaded image metadata")


class ImageListResponse(BaseModel):
    """Response schema for listing multiple images."""
    success: bool = Field(True, description="Request success status")
    message: str = Field("Images retrieved successfully", description="Response message")
    data: List[ImageMetadata] = Field(..., description="List of image metadata")
    total: int = Field(..., description="Total number of images")


class ImageValidationError(BaseModel):
    """Schema for image validation errors."""
    filename: str = Field(..., description="Filename that failed validation")
    errors: List[str] = Field(..., description="List of validation errors")


class BatchUploadResponse(BaseModel):
    """Response schema for batch image uploads."""
    success: bool = Field(True, description="Batch upload completion status")
    message: str = Field(..., description="Batch upload summary message")
    successful_uploads: List[ImageMetadata] = Field(default_factory=list, description="Successfully uploaded images")
    failed_uploads: List[ImageValidationError] = Field(default_factory=list, description="Failed upload attempts")
    total_files: int = Field(..., description="Total files processed")
    successful_count: int = Field(..., description="Number of successful uploads")
    failed_count: int = Field(..., description="Number of failed uploads")


class ImageDeleteResponse(BaseModel):
    """Response schema for image deletion."""
    success: bool = Field(..., description="Deletion success status")
    message: str = Field(..., description="Deletion result message")
    deleted_filename: str = Field(..., description="Name of deleted file")


class ImageStatsResponse(BaseModel):
    """Response schema for storage statistics."""
    success: bool = Field(True, description="Request success status")
    total_images: int = Field(..., description="Total number of stored images")
    total_size_bytes: int = Field(..., description="Total storage size in bytes")
    total_size_formatted: str = Field(..., description="Human-readable total size")
    storage_directory: str = Field(..., description="Storage directory path")
