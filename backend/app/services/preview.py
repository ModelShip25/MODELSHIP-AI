# app/services/preview.py
import cv2
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple
import colorsys
import hashlib

from ..storage.image_store import ImageStore
from ..models.annotation import Annotation

logger = logging.getLogger(__name__)


class PreviewError(Exception):
    """Custom exception for preview generation errors."""
    pass


class PreviewService:
    """Service for generating preview images with bounding boxes."""
    
    def __init__(self):
        self.image_store = ImageStore()
        self.preview_dir = Path("previews")
        self.preview_dir.mkdir(exist_ok=True)
        
        # Default visualization settings
        self.box_thickness = 2
        self.text_thickness = 1
        self.text_scale = 0.5
        self.text_font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_padding = 3
        
        # Cache of class name to color mappings
        self._class_colors = {}
    
    async def generate_preview(
        self,
        image_id: str,
        annotations: Optional[List[Annotation]] = None,
        min_confidence: float = 0.0,
        show_labels: bool = True,
        show_confidence: bool = True,
        box_thickness: Optional[int] = None,
        text_scale: Optional[float] = None
    ) -> str:
        """
        Generate a preview image with bounding boxes drawn.
        
        Args:
            image_id: ID of the image to preview
            annotations: List of annotations to draw (if None, fetches from storage)
            min_confidence: Minimum confidence threshold for showing annotations
            show_labels: Whether to show class labels
            show_confidence: Whether to show confidence scores
            box_thickness: Override default box thickness
            text_scale: Override default text scale
            
        Returns:
            Path to the generated preview image
        """
        try:
            # Get image and annotations
            image_path = await self.image_store.get_image_path(image_id)
            if not annotations:
                annotations = await self.image_store.get_annotations(image_id)
            
            # Read image
            image = cv2.imread(str(image_path))
            if image is None:
                raise PreviewError(f"Failed to read image: {image_path}")
            
            # Filter annotations by confidence
            filtered_annotations = [
                ann for ann in annotations
                if ann.confidence >= min_confidence
            ]
            
            # Draw annotations
            preview = self._draw_annotations(
                image,
                filtered_annotations,
                show_labels=show_labels,
                show_confidence=show_confidence,
                box_thickness=box_thickness or self.box_thickness,
                text_scale=text_scale or self.text_scale
            )
            
            # Save preview
            preview_path = self.preview_dir / f"{image_id}_preview.png"
            cv2.imwrite(str(preview_path), preview)
            
            return str(preview_path)
            
        except Exception as e:
            error_msg = f"Failed to generate preview: {str(e)}"
            logger.error(error_msg)
            raise PreviewError(error_msg)
    
    def _draw_annotations(
        self,
        image: np.ndarray,
        annotations: List[Annotation],
        show_labels: bool = True,
        show_confidence: bool = True,
        box_thickness: int = 2,
        text_scale: float = 0.5
    ) -> np.ndarray:
        """Draw annotations on the image."""
        preview = image.copy()
        
        for ann in annotations:
            # Get color for class
            color = self._get_class_color(ann.class_name)
            
            # Draw bounding box
            p1 = (int(ann.bbox.x_min), int(ann.bbox.y_min))
            p2 = (int(ann.bbox.x_max), int(ann.bbox.y_max))
            cv2.rectangle(preview, p1, p2, color, box_thickness)
            
            if show_labels or show_confidence:
                # Prepare label text
                label_parts = []
                if show_labels:
                    label_parts.append(ann.class_name)
                if show_confidence:
                    conf = f"{ann.confidence:.2f}"
                    label_parts.append(conf)
                label = " ".join(label_parts)
                
                # Calculate text size and background
                (text_w, text_h), baseline = cv2.getTextSize(
                    label,
                    self.text_font,
                    text_scale,
                    self.text_thickness
                )
                
                # Draw label background
                text_x = p1[0]
                text_y = p1[1] - text_h - self.text_padding * 2
                if text_y < 0:  # If label would be off screen, put it inside box
                    text_y = p1[1] + text_h + self.text_padding
                
                cv2.rectangle(
                    preview,
                    (text_x, text_y - baseline),
                    (text_x + text_w + self.text_padding * 2, text_y + text_h),
                    color,
                    -1  # Filled rectangle
                )
                
                # Draw label text
                cv2.putText(
                    preview,
                    label,
                    (text_x + self.text_padding, text_y + text_h - self.text_padding),
                    self.text_font,
                    text_scale,
                    (255, 255, 255),  # White text
                    self.text_thickness,
                    cv2.LINE_AA
                )
        
        return preview
    
    def _get_class_color(self, class_name: str) -> Tuple[int, int, int]:
        """Get a consistent color for a class name using HSV color space."""
        if class_name not in self._class_colors:
            # Generate a hash of the class name
            hash_val = int(hashlib.md5(class_name.encode()).hexdigest(), 16)
            
            # Use hash to generate HSV color (using golden ratio to spread colors)
            hue = (hash_val * 0.618033988749895) % 1.0
            
            # Convert to RGB (always full saturation and value for visibility)
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            
            # Convert to BGR (OpenCV format) with 0-255 range
            bgr = (
                int(rgb[2] * 255),
                int(rgb[1] * 255),
                int(rgb[0] * 255)
            )
            
            self._class_colors[class_name] = bgr
        
        return self._class_colors[class_name]
    
    async def update_preview(
        self,
        image_id: str,
        annotations: List[Annotation]
    ) -> Dict:
        """
        Update preview with new annotations.
        
        Args:
            image_id: ID of the image
            annotations: Updated list of annotations
            
        Returns:
            Dictionary with preview path and metadata
        """
        try:
            # Generate new preview with updated annotations
            preview_path = await self.generate_preview(
                image_id=image_id,
                annotations=annotations
            )
            
            return {
                "preview_path": preview_path,
                "annotation_count": len(annotations),
                "image_id": image_id
            }
            
        except Exception as e:
            error_msg = f"Failed to update preview: {str(e)}"
            logger.error(error_msg)
            raise PreviewError(error_msg)
    
    async def get_preview_metadata(self, image_id: str) -> Dict:
        """
        Get metadata about a preview image.
        
        Args:
            image_id: ID of the image
            
        Returns:
            Dictionary with preview metadata
        """
        try:
            # Get image info
            image_path = await self.image_store.get_image_path(image_id)
            annotations = await self.image_store.get_annotations(image_id)
            
            # Read image to get dimensions
            image = cv2.imread(str(image_path))
            if image is None:
                raise PreviewError(f"Failed to read image: {image_path}")
            
            height, width = image.shape[:2]
            
            # Check if preview exists
            preview_path = self.preview_dir / f"{image_id}_preview.png"
            preview_exists = preview_path.exists()
            
            return {
                "image_id": image_id,
                "original_dimensions": {
                    "width": width,
                    "height": height
                },
                "annotation_count": len(annotations),
                "preview_exists": preview_exists,
                "preview_path": str(preview_path) if preview_exists else None
            }
            
        except Exception as e:
            error_msg = f"Failed to get preview metadata: {str(e)}"
            logger.error(error_msg)
            raise PreviewError(error_msg) 