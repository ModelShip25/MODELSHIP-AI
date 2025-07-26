"""
Service for storing and retrieving images using Supabase.
Handles image validation, storage, and retrieval.
"""

import os
import uuid
from pathlib import Path
import logging
from typing import Dict, List, Optional, BinaryIO, Union, Any, cast, Tuple
from datetime import datetime
import aiofiles
import asyncio
from PIL import Image
import io
import mimetypes
from pydantic import BaseModel
from fastapi import UploadFile, HTTPException

from app.core.config import settings
from app.core.supabase_client import supabase_client
from app.models.annotation import Annotation, BoundingBox

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp']
MAX_IMAGE_DIMENSION = 4096  # Maximum width or height

class ImageMetadata(BaseModel):
    """Metadata for stored images."""
    id: str
    filename: str
    content_type: str
    size: int
    width: int
    height: int
    created_at: datetime
    storage_path: str
    user_id: Optional[str] = None

class ImageStoreError(Exception):
    """Custom exception for image store operations."""
    pass

class ImageStore:
    """Service for storing and retrieving images using Supabase."""
    
    def __init__(self):
        """Initialize Supabase client and storage bucket."""
        try:
            self.supabase = supabase_client
            self.IMAGE_BUCKET = "images"
            
            # Ensure bucket exists
            asyncio.create_task(self._ensure_bucket())
            
        except Exception as e:
            raise ImageStoreError(f"Failed to initialize image store: {str(e)}")
    
    async def _ensure_bucket(self):
        """Ensure required storage bucket exists."""
        try:
            buckets = await self.supabase.storage.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]
            
            if self.IMAGE_BUCKET not in bucket_names:
                await self.supabase.storage.create_bucket(self.IMAGE_BUCKET)
                
        except Exception as e:
            raise ImageStoreError(f"Failed to ensure bucket: {str(e)}")
    
    @staticmethod
    async def _validate_image(file: UploadFile) -> Tuple[int, int, int]:
        """Validate image file and return dimensions."""
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Reset position
        
        if size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE/1024/1024}MB"
            )
        
        # Check mime type
        content_type = file.content_type or mimetypes.guess_type(file.filename or "")[0]
        if not content_type or content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
            )
        
        # Check image dimensions
        try:
            img = Image.open(file.file)
            width, height = img.size
            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                raise HTTPException(
                    status_code=400,
                    detail=f"Image dimensions too large. Maximum allowed is {MAX_IMAGE_DIMENSION}px"
                )
            file.file.seek(0)  # Reset position
            return width, height, size
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid image file"
            )

    async def store_image(
        self,
        file: UploadFile,
        user_id: Optional[str] = None
    ) -> ImageMetadata:
        """Store an image file and its metadata."""
        try:
            # Validate image
            width, height, size = await self._validate_image(file)
            
            # Generate unique ID and filename
            image_id = str(uuid.uuid4())
            filename = file.filename or f"{image_id}.jpg"
            
            # Read file content
            content = await file.read()
            
            # Upload with retry
            max_retries = 3
            storage_path = None
            
            for attempt in range(max_retries):
                try:
                    result = await self.supabase.storage \
                        .from_(self.IMAGE_BUCKET) \
                        .upload(
                            path=f"{image_id}/{filename}",
                            file=content,
                            file_options=None  # Let Supabase handle content type
                        )
                    storage_path = result.path if hasattr(result, 'path') else str(result)
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Upload attempt {attempt + 1} failed, retrying...")
                    await asyncio.sleep(1)  # Wait before retry
            
            if not storage_path:
                raise ImageStoreError("Failed to get storage path from upload result")
            
            # Create metadata
            metadata = ImageMetadata(
                id=image_id,
                filename=filename,
                content_type=file.content_type or "application/octet-stream",
                size=size,
                width=width,
                height=height,
                created_at=datetime.utcnow(),
                storage_path=storage_path,
                user_id=user_id
            )
            
            # Store metadata in database
            await self.supabase.table("images") \
                .insert(metadata.dict()) \
                .execute()
            
            return metadata
            
        except Exception as e:
            raise ImageStoreError(f"Failed to store image: {str(e)}")
    
    async def store_annotations(
        self,
        image_id: str,
        annotations: List[Annotation]
    ):
        """Store annotations for an image."""
        try:
            # Convert annotations to database format
            annotation_data = [
                {
                    "image_id": image_id,
                    "class_id": ann.class_id,
                    "class_name": ann.class_name,
                    "confidence": ann.confidence,
                    "bbox": {
                        "x_min": ann.bbox.x_min,
                        "y_min": ann.bbox.y_min,
                        "x_max": ann.bbox.x_max,
                        "y_max": ann.bbox.y_max
                    }
                }
                for ann in annotations
            ]
            
            # Insert annotations in batches of 100
            batch_size = 100
            for i in range(0, len(annotation_data), batch_size):
                batch = annotation_data[i:i + batch_size]
                await self.supabase.table("annotations") \
                    .insert(batch) \
                    .execute()
                
        except Exception as e:
            raise ImageStoreError(f"Failed to store annotations: {str(e)}")
<<<<<<< HEAD
=======
    
    async def get_annotations(self, image_id: str) -> List[Annotation]:
        """Get annotations for an image."""
        try:
            result = self.supabase.table("annotations") \
                .select("*") \
                .eq("image_id", image_id) \
                .execute()
            
            if not result.data:
                return []
            
            # Convert to Annotation objects
            annotations = []
            for data in result.data:
                bbox_data = data["bbox"]
                ann_id = str(uuid.uuid4())  # Generate ID if not present
                ann = Annotation(
                    id=ann_id,
                    image_id=image_id,
                    class_name=data["class_name"],
                    class_id=data["class_id"],
                    confidence=data["confidence"],
                    bbox=BoundingBox(
                        x_min=bbox_data["x_min"],
                        y_min=bbox_data["y_min"],
                        x_max=bbox_data["x_max"],
                        y_max=bbox_data["y_max"]
                    ),
                    area=float(
                        (bbox_data["x_max"] - bbox_data["x_min"]) *
                        (bbox_data["y_max"] - bbox_data["y_min"])
                    ),
                    source="yolox"
                )
                annotations.append(ann)
            
            return annotations
            
        except Exception as e:
            raise ImageStoreError(f"Failed to get annotations: {str(e)}")
    
    async def delete_image(self, image_id: str):
        """Delete an image and its associated data."""
        try:
            # Get image info
            metadata = await self.get_image_metadata(image_id)
            
            # Delete from storage
            filename = Path(metadata.storage_path).name
            self.supabase.storage \
                .from_(self.IMAGES_BUCKET) \
                .remove([filename])
            
            # Delete preview if exists
            if metadata.preview_path:
                preview_name = Path(metadata.preview_path).name
                self.supabase.storage \
                    .from_(self.PREVIEWS_BUCKET) \
                    .remove([preview_name])
            
            # Delete from database (cascade to annotations)
            self.supabase.table("images") \
                .delete() \
                .eq("id", image_id) \
                .execute()
            
        except Exception as e:
            raise ImageStoreError(f"Failed to delete image: {str(e)}")
    
    async def cleanup_temp(self):
        """Clean up temporary files."""
        try:
            for file in self.temp_dir.iterdir():
                if file.is_file():
                    file.unlink()
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {str(e)}")

    async def save_image(
        self,
        file: "UploadFile",
        user_id: Optional[str] = None
    ) -> ImageMetadata:
        """
        Save an uploaded image file (wrapper for store_image).
        
        Args:
            file: FastAPI UploadFile object
            user_id: Optional user ID for ownership
            
        Returns:
            ImageMetadata with storage details
        """
        try:
            # Read file content first
            content = await file.read()
            file_obj = io.BytesIO(content)
            
            # Store the image using the existing method
            metadata = await self.store_image(
                file=file_obj,
                filename=file.filename if file.filename else "untitled.jpg",
                content_type=file.content_type,
                user_id=user_id
            )
            
            return metadata
            
        except Exception as e:
            raise ImageStoreError(f"Failed to save image: {str(e)}")

    async def get_storage_info(self) -> Dict:
        """Get storage service information and statistics."""
        try:
            # Get bucket info (simplified for MVP)
            return {
                "service": "supabase",
                "status": "operational",
                "buckets": [self.IMAGES_BUCKET, self.PREVIEWS_BUCKET],
                "temp_directory": str(self.temp_dir)
            }
        except Exception as e:
            raise ImageStoreError(f"Failed to get storage info: {str(e)}")

    def get_storage_stats(self) -> Dict:
        """Get storage statistics (synchronous version for compatibility)."""
        try:
            return {
                "total_images": 0,  # Would query database in production
                "total_size": 0,
                "service": "supabase",
                "status": "operational"
            }
        except Exception as e:
            raise ImageStoreError(f"Failed to get storage stats: {str(e)}")

    def image_exists(self, filename: str) -> bool:
        """Check if an image exists (simplified for MVP)."""
        try:
            # In production, this would query the database
            return False  # Placeholder implementation
        except Exception as e:
            raise ImageStoreError(f"Failed to check image existence: {str(e)}")
>>>>>>> 2ced259340e3e167b468bd712cf7a750fb4e3567
