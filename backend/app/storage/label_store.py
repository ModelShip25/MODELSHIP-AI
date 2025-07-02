# app/storage/label_store.py
import os
import uuid
from pathlib import Path
import logging
from typing import Dict, List, Optional, BinaryIO, Union
from datetime import datetime
import json
import aiofiles
import asyncio
from pydantic import BaseModel

from supabase import create_client, Client

from ..core.config import settings
from ..models.annotation import Annotation, BoundingBox

logger = logging.getLogger(__name__)


class ExportMetadata(BaseModel):
    """Metadata for exported files."""
    id: str
    job_id: str
    format: str  # 'yolo', 'coco', 'csv'
    filename: str
    created_at: datetime
    storage_path: str
    file_size: int
    user_id: Optional[str] = None


class LabelStoreError(Exception):
    """Custom exception for label storage errors."""
    pass


class LabelStore:
    """Service for storing and retrieving annotations, exports, and previews."""
    
    def __init__(self):
        """Initialize Supabase client and storage buckets."""
        try:
            self.supabase: Client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
            
            # Storage bucket names
            self.EXPORTS_BUCKET = "exports"
            self.PREVIEWS_BUCKET = "previews"
            
            # Local temp directory for processing
            self.temp_dir = Path("temp")
            self.temp_dir.mkdir(exist_ok=True)
            
            # Ensure buckets exist
            self._ensure_buckets()
            
        except Exception as e:
            raise LabelStoreError(f"Failed to initialize storage: {str(e)}")
    
    def _ensure_buckets(self):
        """Ensure required storage buckets exist."""
        try:
            buckets = self.supabase.storage.list_buckets()
            existing = {b["name"] for b in buckets}
            
            if self.EXPORTS_BUCKET not in existing:
                self.supabase.storage.create_bucket(
                    self.EXPORTS_BUCKET,
                    public=False  # Exports are private
                )
            
            if self.PREVIEWS_BUCKET not in existing:
                self.supabase.storage.create_bucket(
                    self.PREVIEWS_BUCKET,
                    public=True  # Previews can be public
                )
                
        except Exception as e:
            raise LabelStoreError(f"Failed to create buckets: {str(e)}")
    
    async def store_annotations(
        self,
        image_id: str,
        annotations: List[Annotation],
        job_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Store annotations for an image.
        
        Args:
            image_id: ID of the image
            annotations: List of annotations
            job_id: Optional job ID for batch processing
            user_id: Optional user ID for ownership
        """
        try:
            # Convert annotations to database format
            annotation_data = [
                {
                    "image_id": image_id,
                    "job_id": job_id,
                    "user_id": user_id,
                    "class_name": ann.class_name,
                    "class_id": ann.class_id,
                    "confidence": ann.confidence,
                    "bbox": {
                        "x_min": ann.bbox.x_min,
                        "y_min": ann.bbox.y_min,
                        "x_max": ann.bbox.x_max,
                        "y_max": ann.bbox.y_max
                    },
                    "created_at": datetime.utcnow().isoformat()
                }
                for ann in annotations
            ]
            
            # Store in database
            self.supabase.table("annotations") \
                .insert(annotation_data) \
                .execute()
            
        except Exception as e:
            raise LabelStoreError(f"Failed to store annotations: {str(e)}")
    
    async def get_annotations(
        self,
        image_id: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> List[Annotation]:
        """
        Get annotations by image ID or job ID.
        
        Args:
            image_id: Optional image ID to filter by
            job_id: Optional job ID to filter by
            
        Returns:
            List of annotations
        """
        try:
            query = self.supabase.table("annotations").select("*")
            
            if image_id:
                query = query.eq("image_id", image_id)
            if job_id:
                query = query.eq("job_id", job_id)
                
            result = query.execute()
            
            if not result.data:
                return []
            
            # Convert to Annotation objects
            annotations = []
            for data in result.data:
                bbox_data = data["bbox"]
                ann = Annotation(
                    bbox=BoundingBox(
                        x_min=bbox_data["x_min"],
                        y_min=bbox_data["y_min"],
                        x_max=bbox_data["x_max"],
                        y_max=bbox_data["y_max"]
                    ),
                    class_name=data["class_name"],
                    class_id=data["class_id"],
                    confidence=data["confidence"]
                )
                annotations.append(ann)
            
            return annotations
            
        except Exception as e:
            raise LabelStoreError(f"Failed to get annotations: {str(e)}")
    
    async def store_export(
        self,
        job_id: str,
        format: str,
        file: BinaryIO,
        filename: str,
        user_id: Optional[str] = None
    ) -> ExportMetadata:
        """
        Store an export file.
        
        Args:
            job_id: ID of the labeling job
            format: Export format ('yolo', 'coco', 'csv')
            file: File-like object containing export data
            filename: Original filename
            user_id: Optional user ID for ownership
            
        Returns:
            ExportMetadata with storage details
        """
        try:
            # Generate UUID for storage
            export_id = str(uuid.uuid4())
            ext = Path(filename).suffix
            storage_name = f"{export_id}{ext}"
            
            # Upload to Supabase
            result = self.supabase.storage \
                .from_(self.EXPORTS_BUCKET) \
                .upload(
                    storage_name,
                    file,
                    file_options={"content-type": "application/octet-stream"}
                )
            
            if not result or "error" in result:
                raise LabelStoreError(
                    f"Export upload failed: {result.get('error', 'Unknown error')}"
                )
            
            # Get storage path
            storage_path = self.supabase.storage \
                .from_(self.EXPORTS_BUCKET) \
                .get_public_url(storage_name)
            
            # Get file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            # Create metadata
            metadata = ExportMetadata(
                id=export_id,
                job_id=job_id,
                format=format,
                filename=filename,
                created_at=datetime.utcnow(),
                storage_path=storage_path,
                file_size=file_size,
                user_id=user_id
            )
            
            # Store metadata in database
            self.supabase.table("exports").insert({
                "id": metadata.id,
                "job_id": metadata.job_id,
                "format": metadata.format,
                "filename": metadata.filename,
                "created_at": metadata.created_at.isoformat(),
                "storage_path": metadata.storage_path,
                "file_size": metadata.file_size,
                "user_id": metadata.user_id
            }).execute()
            
            return metadata
            
        except Exception as e:
            raise LabelStoreError(f"Failed to store export: {str(e)}")
    
    async def get_export_metadata(
        self,
        export_id: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Union[ExportMetadata, List[ExportMetadata]]:
        """
        Get metadata for export(s).
        
        Args:
            export_id: Optional specific export ID
            job_id: Optional job ID to get all exports for
            
        Returns:
            Single ExportMetadata or list of ExportMetadata
        """
        try:
            query = self.supabase.table("exports").select("*")
            
            if export_id:
                result = query.eq("id", export_id).single().execute()
                if not result.data:
                    raise LabelStoreError(f"Export not found: {export_id}")
                return ExportMetadata(**result.data)
            
            elif job_id:
                result = query.eq("job_id", job_id).execute()
                return [ExportMetadata(**data) for data in result.data]
            
            else:
                raise LabelStoreError("Must provide either export_id or job_id")
            
        except Exception as e:
            raise LabelStoreError(f"Failed to get export metadata: {str(e)}")
    
    async def delete_export(self, export_id: str):
        """Delete an export file and its metadata."""
        try:
            # Get export info
            metadata = await self.get_export_metadata(export_id)
            
            # Delete from storage
            filename = Path(metadata.storage_path).name
            self.supabase.storage \
                .from_(self.EXPORTS_BUCKET) \
                .remove([filename])
            
            # Delete from database
            self.supabase.table("exports") \
                .delete() \
                .eq("id", export_id) \
                .execute()
            
        except Exception as e:
            raise LabelStoreError(f"Failed to delete export: {str(e)}")
    
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
                raise LabelStoreError(
                    f"Preview upload failed: {result.get('error', 'Unknown error')}"
                )
            
            # Get public URL
            preview_url = self.supabase.storage \
                .from_(self.PREVIEWS_BUCKET) \
                .get_public_url(preview_name)
            
            return preview_url
            
        except Exception as e:
            raise LabelStoreError(f"Failed to store preview: {str(e)}")
    
    async def get_preview_url(self, image_id: str) -> Optional[str]:
        """Get the public URL for a preview image."""
        try:
            preview_name = f"{image_id}_preview.png"
            return self.supabase.storage \
                .from_(self.PREVIEWS_BUCKET) \
                .get_public_url(preview_name)
        except Exception as e:
            logger.error(f"Failed to get preview URL: {str(e)}")
            return None
    
    async def delete_preview(self, image_id: str):
        """Delete a preview image."""
        try:
            preview_name = f"{image_id}_preview.png"
            self.supabase.storage \
                .from_(self.PREVIEWS_BUCKET) \
                .remove([preview_name])
        except Exception as e:
            raise LabelStoreError(f"Failed to delete preview: {str(e)}")
    
    async def cleanup_temp(self):
        """Clean up temporary files."""
        try:
            for file in self.temp_dir.iterdir():
                if file.is_file():
                    file.unlink()
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {str(e)}") 