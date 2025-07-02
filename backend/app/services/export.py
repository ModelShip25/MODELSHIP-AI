# app/services/export.py
import os
import json
import csv
import shutil
from typing import Dict, List, Optional
from enum import Enum
import uuid
from datetime import datetime
import logging
from pathlib import Path
import zipfile

from ..storage.image_store import ImageStore
from ..models.annotation import Annotation, YOLOAnnotation, COCOAnnotation
from ..core.utils import create_success_response, create_error_response

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""
    YOLO = "yolo"
    COCO = "coco"
    CSV = "csv"
    ZIP = "zip"


class ExportError(Exception):
    """Custom exception for export service errors."""
    pass


class ExportService:
    """Service for exporting labeled data in various formats."""
    
    def __init__(self):
        self.image_store = ImageStore()
        self.export_dir = Path("exports")  # Temporary export storage
        self.export_dir.mkdir(exist_ok=True)
        self._jobs = {}  # In-memory job storage
        
    async def create_export(
        self,
        format: ExportFormat,
        image_ids: List[str],
        include_images: bool = False,
        include_previews: bool = False,
        min_confidence: float = 0.0
    ) -> Dict:
        """
        Create an export in the specified format.
        
        Args:
            format: Export format (YOLO, COCO, CSV, ZIP)
            image_ids: List of image IDs to export
            include_images: Whether to include original images
            include_previews: Whether to include preview images
            min_confidence: Minimum confidence threshold for annotations
            
        Returns:
            Dict containing:
            - job_id: Export job identifier
            - file_path: Path to export file (if ready)
            - filename: Suggested download filename
            - media_type: Content type for download
            - estimated_size: Estimated export size in bytes
        """
        try:
            job_id = str(uuid.uuid4())
            export_path = self.export_dir / job_id
            export_path.mkdir(exist_ok=True)
            
            # Initialize job tracking
            self._jobs[job_id] = {
                "status": "processing",
                "start_time": datetime.utcnow(),
                "format": format,
                "total_images": len(image_ids),
                "processed_images": 0,
                "export_path": str(export_path),
                "errors": []
            }
            
            # Get annotations for all images
            annotations = await self._get_annotations(image_ids, min_confidence)
            
            # Create export based on format
            if format == ExportFormat.YOLO:
                result = await self._create_yolo_export(
                    job_id, annotations, image_ids, include_images
                )
            elif format == ExportFormat.COCO:
                result = await self._create_coco_export(
                    job_id, annotations, image_ids, include_images
                )
            elif format == ExportFormat.CSV:
                result = await self._create_csv_export(
                    job_id, annotations, image_ids, include_images
                )
            elif format == ExportFormat.ZIP:
                result = await self._create_zip_export(
                    job_id, annotations, image_ids, include_images, include_previews
                )
            
            # Update job completion
            self._jobs[job_id].update({
                "status": "completed",
                "end_time": datetime.utcnow(),
                **result
            })
            
            return {
                "job_id": job_id,
                **result
            }
            
        except Exception as e:
            error_msg = f"Export creation failed: {str(e)}"
            logger.error(error_msg)
            if job_id in self._jobs:
                self._jobs[job_id].update({
                    "status": "failed",
                    "error": error_msg
                })
            raise ExportError(error_msg)

    async def get_export_status(self, job_id: str) -> Dict:
        """Get status and details of an export job."""
        try:
            if job_id not in self._jobs:
                raise ExportError(f"Export job {job_id} not found")
                
            return self._jobs[job_id]
            
        except Exception as e:
            logger.error(f"Failed to get export status: {str(e)}")
            raise ExportError(f"Failed to get export status: {str(e)}")

    async def cleanup_export(self, job_id: str):
        """Clean up export files after download."""
        try:
            if job_id in self._jobs:
                export_path = Path(self._jobs[job_id]["export_path"])
                if export_path.exists():
                    shutil.rmtree(export_path)
                del self._jobs[job_id]
                
        except Exception as e:
            logger.error(f"Failed to cleanup export {job_id}: {str(e)}")

    async def _get_annotations(
        self,
        image_ids: List[str],
        min_confidence: float
    ) -> Dict[str, List[Annotation]]:
        """Get annotations for images, filtered by confidence."""
        annotations = {}
        for image_id in image_ids:
            try:
                # Get annotations from storage/DB
                image_annotations = await self.image_store.get_annotations(image_id)
                
                # Filter by confidence
                filtered_annotations = [
                    ann for ann in image_annotations
                    if ann.confidence >= min_confidence
                ]
                
                annotations[image_id] = filtered_annotations
                
            except Exception as e:
                logger.warning(f"Failed to get annotations for image {image_id}: {str(e)}")
                
        return annotations

    async def _create_yolo_export(
        self,
        job_id: str,
        annotations: Dict[str, List[Annotation]],
        image_ids: List[str],
        include_images: bool
    ) -> Dict:
        """Create YOLO format export."""
        try:
            export_path = Path(self._jobs[job_id]["export_path"])
            labels_dir = export_path / "labels"
            labels_dir.mkdir(exist_ok=True)
            
            if include_images:
                images_dir = export_path / "images"
                images_dir.mkdir(exist_ok=True)
            
            # Create YOLO annotations
            for image_id, image_anns in annotations.items():
                # Convert to YOLO format
                yolo_annotations = [
                    YOLOAnnotation.from_annotation(ann)
                    for ann in image_anns
                ]
                
                # Write label file
                label_file = labels_dir / f"{image_id}.txt"
                with open(label_file, "w") as f:
                    for ann in yolo_annotations:
                        f.write(ann.to_yolo_string() + "\n")
                
                if include_images:
                    # Copy image file
                    image_path = await self.image_store.get_image_path(image_id)
                    shutil.copy2(
                        image_path,
                        images_dir / f"{image_id}{Path(image_path).suffix}"
                    )
            
            # Create classes.txt
            classes = sorted(set(
                ann.class_name
                for anns in annotations.values()
                for ann in anns
            ))
            with open(export_path / "classes.txt", "w") as f:
                f.write("\n".join(classes))
            
            # Create README
            with open(export_path / "README.txt", "w") as f:
                f.write("YOLO Format Dataset\n\n")
                f.write(f"Total Images: {len(image_ids)}\n")
                f.write(f"Classes: {len(classes)}\n")
                f.write("\nDirectory Structure:\n")
                f.write("- labels/: YOLO format annotation files\n")
                if include_images:
                    f.write("- images/: Original image files\n")
                f.write("- classes.txt: List of class names\n")
            
            # Create zip file
            zip_path = export_path / "export.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in export_path.rglob("*"):
                    if file != zip_path and file.is_file():
                        zf.write(file, file.relative_to(export_path))
            
            return {
                "file_path": str(zip_path),
                "filename": f"yolo_export_{job_id}.zip",
                "media_type": "application/zip",
                "ready": True
            }
            
        except Exception as e:
            raise ExportError(f"YOLO export failed: {str(e)}")

    async def _create_coco_export(
        self,
        job_id: str,
        annotations: Dict[str, List[Annotation]],
        image_ids: List[str],
        include_images: bool
    ) -> Dict:
        """Create COCO JSON format export."""
        try:
            export_path = Path(self._jobs[job_id]["export_path"])
            
            if include_images:
                images_dir = export_path / "images"
                images_dir.mkdir(exist_ok=True)
            
            # Prepare COCO format data
            classes = sorted(set(
                ann.class_name
                for anns in annotations.values()
                for ann in anns
            ))
            
            coco_data = {
                "info": {
                    "description": "ModelShip Export",
                    "date_created": datetime.utcnow().isoformat()
                },
                "categories": [
                    {"id": i, "name": name}
                    for i, name in enumerate(classes)
                ],
                "images": [],
                "annotations": []
            }
            
            ann_id = 1
            for image_id in image_ids:
                # Get image info
                image_path = await self.image_store.get_image_path(image_id)
                image_info = await self.image_store.get_image_metadata(image_id)
                
                # Add image to COCO format
                coco_data["images"].append({
                    "id": image_id,
                    "file_name": Path(image_path).name,
                    "width": image_info.width,
                    "height": image_info.height
                })
                
                if include_images:
                    # Copy image file
                    shutil.copy2(
                        image_path,
                        images_dir / Path(image_path).name
                    )
                
                # Convert annotations to COCO format
                for ann in annotations.get(image_id, []):
                    coco_ann = COCOAnnotation.from_annotation(
                        ann,
                        annotation_id=ann_id,
                        category_id=classes.index(ann.class_name)
                    )
                    coco_data["annotations"].append(coco_ann.dict())
                    ann_id += 1
            
            # Write COCO JSON
            with open(export_path / "annotations.json", "w") as f:
                json.dump(coco_data, f, indent=2)
            
            # Create zip if including images
            if include_images:
                zip_path = export_path / "export.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.write(
                        export_path / "annotations.json",
                        "annotations.json"
                    )
                    for image in images_dir.iterdir():
                        zf.write(image, f"images/{image.name}")
                        
                return {
                    "file_path": str(zip_path),
                    "filename": f"coco_export_{job_id}.zip",
                    "media_type": "application/zip",
                    "ready": True
                }
            
            return {
                "file_path": str(export_path / "annotations.json"),
                "filename": f"coco_export_{job_id}.json",
                "media_type": "application/json",
                "ready": True
            }
            
        except Exception as e:
            raise ExportError(f"COCO export failed: {str(e)}")

    async def _create_csv_export(
        self,
        job_id: str,
        annotations: Dict[str, List[Annotation]],
        image_ids: List[str],
        include_images: bool
    ) -> Dict:
        """Create CSV format export."""
        try:
            export_path = Path(self._jobs[job_id]["export_path"])
            
            if include_images:
                images_dir = export_path / "images"
                images_dir.mkdir(exist_ok=True)
            
            # Create CSV file
            csv_path = export_path / "annotations.csv"
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "image_id",
                    "image_name",
                    "class_name",
                    "confidence",
                    "x_min",
                    "y_min",
                    "x_max",
                    "y_max",
                    "area"
                ])
                
                for image_id in image_ids:
                    image_path = await self.image_store.get_image_path(image_id)
                    image_name = Path(image_path).name
                    
                    if include_images:
                        # Copy image file
                        shutil.copy2(
                            image_path,
                            images_dir / image_name
                        )
                    
                    # Write annotations
                    for ann in annotations.get(image_id, []):
                        writer.writerow([
                            image_id,
                            image_name,
                            ann.class_name,
                            ann.confidence,
                            ann.bbox.x_min,
                            ann.bbox.y_min,
                            ann.bbox.x_max,
                            ann.bbox.y_max,
                            ann.area
                        ])
            
            # Create zip if including images
            if include_images:
                zip_path = export_path / "export.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.write(csv_path, "annotations.csv")
                    for image in images_dir.iterdir():
                        zf.write(image, f"images/{image.name}")
                        
                return {
                    "file_path": str(zip_path),
                    "filename": f"csv_export_{job_id}.zip",
                    "media_type": "application/zip",
                    "ready": True
                }
            
            return {
                "file_path": str(csv_path),
                "filename": f"annotations_{job_id}.csv",
                "media_type": "text/csv",
                "ready": True
            }
            
        except Exception as e:
            raise ExportError(f"CSV export failed: {str(e)}")

    async def _create_zip_export(
        self,
        job_id: str,
        annotations: Dict[str, List[Annotation]],
        image_ids: List[str],
        include_images: bool,
        include_previews: bool
    ) -> Dict:
        """Create complete ZIP export with all formats."""
        try:
            export_path = Path(self._jobs[job_id]["export_path"])
            
            # Create all formats
            await self._create_yolo_export(
                job_id, annotations, image_ids, include_images
            )
            await self._create_coco_export(
                job_id, annotations, image_ids, include_images
            )
            await self._create_csv_export(
                job_id, annotations, image_ids, include_images
            )
            
            if include_previews:
                previews_dir = export_path / "previews"
                previews_dir.mkdir(exist_ok=True)
                
                for image_id in image_ids:
                    try:
                        preview_path = await self.image_store.get_preview_path(image_id)
                        if preview_path:
                            shutil.copy2(
                                preview_path,
                                previews_dir / f"{image_id}_preview.png"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to copy preview for {image_id}: {str(e)}")
            
            # Create final zip with everything
            zip_path = export_path / "complete_export.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in export_path.rglob("*"):
                    if file != zip_path and file.is_file():
                        zf.write(file, file.relative_to(export_path))
            
            return {
                "file_path": str(zip_path),
                "filename": f"complete_export_{job_id}.zip",
                "media_type": "application/zip",
                "ready": True
            }
            
        except Exception as e:
            raise ExportError(f"ZIP export failed: {str(e)}")