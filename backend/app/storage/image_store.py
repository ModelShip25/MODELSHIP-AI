# app/storage/image_store.py
import os
import uuid
from pathlib import Path
import logging
from typing import Dict, List, Optional, BinaryIO, Union, Any, cast
from datetime import datetime
import aiofiles
import asyncio
from PIL import Image
import io
import mimetypes
from pydantic import BaseModel
from fastapi import UploadFile
from postgrest import APIResponse

from app.core.config import settings
from app.core.supabase_client import supabase_client
from app.models.annotation import Annotation, BoundingBox

logger = logging.getLogger(__name__)


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
    preview_path: Optional[str] = None
    user_id: Optional[str] = None


class ImageStoreError(Exception):
    """Custom exception for image storage errors."""
    pass


class ImageStore:
    """Service for storing and retrieving images using Supabase."""
    
    def __init__(self):
        """Initialize Supabase client and storage buckets."""
        try:
            self.supabase = supabase_client
            
            # Storage bucket names
            self.IMAGES_BUCKET = "images"
            self.PREVIEWS_BUCKET = "previews"
            
            # Local temp directory for processing
            self.temp_dir = Path("temp")
            self.temp_dir.mkdir(exist_ok=True)
            
            # Ensure buckets exist
            self._ensure_buckets()
            
        except Exception as e:
            raise ImageStoreError(f"Failed to initialize storage: {str(e)}")
    
    def _ensure_buckets(self):
        """Ensure required storage buckets exist."""
        try:
            buckets = self.supabase.storage.list_buckets()
            existing = {b["name"] for b in buckets}
            
            if self.IMAGES_BUCKET not in existing:
                self.supabase.storage.create_bucket(
                    self.IMAGES_BUCKET,
                    options={"public": False}
                )
            
            if self.PREVIEWS_BUCKET not in existing:
                self.supabase.storage.create_bucket(
                    self.PREVIEWS_BUCKET,
                    options={"public": True}  # Previews can be public for easy display
                )
                
        except Exception as e:
            raise ImageStoreError(f"Failed to create buckets: {str(e)}")
    
    async def store_image(
        self,
        file: BinaryIO,
        filename: str,
        content_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> ImageMetadata:
        """
        Store an image file in Supabase storage.
        
        Args:
            file: File-like object containing image data
            filename: Original filename
            content_type: MIME type (detected if not provided)
            user_id: Optional user ID for ownership
            
        Returns:
            ImageMetadata with storage details
        """
        try:
            # Generate UUID for storage
            image_id = str(uuid.uuid4())
            ext = Path(filename).suffix
            storage_name = f"{image_id}{ext}"
            
            # Get content type if not provided
            if not content_type:
                content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
            
            # Read image for metadata
            image_data = file.read()
            
            with Image.open(io.BytesIO(image_data)) as img:
                width, height = img.size
            
            # Upload to Supabase
            bucket = self.supabase.storage.from_(self.IMAGES_BUCKET)
            result = bucket.upload(
                path=storage_name,
                file=image_data,
                file_options={"contentType": content_type}
            )
            
            if isinstance(result, dict) and result.get("error"):
                raise ImageStoreError(
                    f"Upload failed: {result.get('error', 'Unknown error')}"
                )
            
            # Get storage path
            storage_path = bucket.get_public_url(storage_name)
            
            # Create metadata
            metadata = ImageMetadata(
                id=image_id,
                filename=filename,
                content_type=content_type,
                size=len(image_data),
                width=width,
                height=height,
                created_at=datetime.utcnow(),
                storage_path=storage_path,
                user_id=user_id
            )
            
            # Store metadata in database
            response = self.supabase.table("images").insert({
                "id": metadata.id,
                "filename": metadata.filename,
                "content_type": metadata.content_type,
                "size": metadata.size,
                "width": metadata.width,
                "height": metadata.height,
                "storage_path": metadata.storage_path,
                "user_id": metadata.user_id
            }).execute()
            
            return metadata
            
        except Exception as e:
            raise ImageStoreError(f"Failed to store image: {str(e)}")
    
    async def get_image_path(self, image_id: str) -> str:
        """Get the storage path for an image."""
        try:
            result = self.supabase.table("images") \
                .select("storage_path") \
                .eq("id", image_id) \
                .single() \
                .execute()
            
            if not result.data:
                raise ImageStoreError(f"Image not found: {image_id}")
            
            return result.data["storage_path"]
            
        except Exception as e:
            raise ImageStoreError(f"Failed to get image path: {str(e)}")
    
    async def get_image_metadata(self, image_id: str) -> ImageMetadata:
        """Get metadata for an image."""
        try:
            result = self.supabase.table("images") \
                .select("*") \
                .eq("id", image_id) \
                .single() \
                .execute()
            
            if not result.data:
                raise ImageStoreError(f"Image not found: {image_id}")
            
            return ImageMetadata(**result.data)
            
        except Exception as e:
            raise ImageStoreError(f"Failed to get metadata: {str(e)}")
    
    async def store_preview(
        self,
        image_id: str,
        preview_file: Union[BinaryIO, Path],
        content_type: str = "image/png"
    ) -> str:
        """
        Store a preview image.
        
        Args:
            image_id: ID of the original image
            preview_file: Preview image file or path
            content_type: MIME type of preview
            
        Returns:
            Public URL of stored preview
        """
        try:
            preview_name = f"{image_id}_preview.png"
            
            # Handle Path input
            if isinstance(preview_file, Path):
                preview_data = preview_file.read_bytes()
            else:
                preview_data = preview_file.read()
            
            # Upload preview
            result = self.supabase.storage \
                .from_(self.PREVIEWS_BUCKET) \
                .upload(
                    preview_name,
                    preview_data,
                    file_options={"content-type": content_type}
                )
            
            if not result or "error" in result:
                raise ImageStoreError(
                    f"Preview upload failed: {result.get('error', 'Unknown error')}"
                )
            
            # Get public URL
            preview_url = self.supabase.storage \
                .from_(self.PREVIEWS_BUCKET) \
                .get_public_url(preview_name)
            
            # Update image record
            self.supabase.table("images") \
                .update({"preview_path": preview_url}) \
                .eq("id", image_id) \
                .execute()
            
            return preview_url
            
        except Exception as e:
            raise ImageStoreError(f"Failed to store preview: {str(e)}")
    
    async def get_preview_path(self, image_id: str) -> Optional[str]:
        """Get the public URL for a preview image if it exists."""
        try:
            result = self.supabase.table("images") \
                .select("preview_path") \
                .eq("id", image_id) \
                .single() \
                .execute()
            
            if not result.data:
                return None
            
            return result.data.get("preview_path")
            
        except Exception as e:
            logger.error(f"Failed to get preview path: {str(e)}")
            return None
    
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
                    "class_name": ann.class_name,
                    "class_id": ann.class_id,
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
            
            # Store in database
            self.supabase.table("annotations") \
                .insert(annotation_data) \
                .execute()
            
        except Exception as e:
            raise ImageStoreError(f"Failed to store annotations: {str(e)}")
    
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
                    area=float(bbox_data["x_max"] * bbox_data["y_max"] - bbox_data["x_min"] * bbox_data["y_min"]),
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
