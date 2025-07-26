"""
Service for sliced image detection using SAHI.
"""

import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import uuid

from sahi.slicing import slice_image, SliceImageResult
from sahi.prediction import ObjectPrediction
from sahi.postprocess.combine import postprocess_object_predictions

from .detector import YOLOXDetector, DetectorError
from ..models.annotation import Annotation, BoundingBox

logger = logging.getLogger(__name__)

@dataclass
class SliceConfig:
    """Configuration for image slicing."""
    slice_height: int = 512
    slice_width: int = 512
    overlap_height_ratio: float = 0.2
    overlap_width_ratio: float = 0.2

class SAHIWrapper:
    """Wrapper for SAHI sliced inference."""
    
    def __init__(
        self,
        detector: YOLOXDetector,
        slice_config: Optional[SliceConfig] = None
    ):
        """Initialize SAHI wrapper.
        
        Args:
            detector: YOLOX detector instance
            slice_config: Configuration for image slicing
        """
        self.detector = detector
        self.slice_config = slice_config or SliceConfig()
        
    def predict(self, image: np.ndarray) -> List[Annotation]:
        """Run sliced inference on image.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of detected annotations
        """
        # Convert numpy array to PIL Image
        pil_image = Image.fromarray(image)
        
        # Slice image
        slice_result = slice_image(
            image=pil_image,
            slice_height=self.slice_config.slice_height,
            slice_width=self.slice_config.slice_width,
            overlap_height_ratio=self.slice_config.overlap_height_ratio,
            overlap_width_ratio=self.slice_config.overlap_width_ratio
        )
        
        # Run detection on slices
        predictions = []
        for slice_data in slice_result.images:
            try:
                slice_predictions = self.detector.detect(np.array(slice_data))
                # Convert to SAHI ObjectPrediction format
                sahi_predictions = [
                    ObjectPrediction(
                        bbox=pred["bbox"],
                        category_id=pred["class_id"],
                        category_name=str(pred["class_id"]),  # Use class_id as name if not available
                        score=pred["confidence"]
                    ) for pred in slice_predictions
                ]
                predictions.extend(sahi_predictions)
            except DetectorError as e:
                logger.warning(f"Detection failed for slice: {e}")
                continue
                
        # Merge predictions using postprocess_object_predictions function
        merged_predictions = postprocess_object_predictions(
            object_predictions=predictions,
            match_threshold=0.5,
            match_metric="IOU"
        )
        
        # Convert to annotations
        annotations = []
        for pred in merged_predictions:
            bbox = BoundingBox(
                x_min=pred.bbox[0],
                y_min=pred.bbox[1],
                x_max=pred.bbox[2],
                y_max=pred.bbox[3]
            )
            annotation = Annotation(
                id=str(uuid.uuid4()),
                image_id="",  # Will be set by caller
                class_id=pred.category.id,
                class_name=pred.category.name,
                confidence=pred.score,
                bbox=bbox,
                area=bbox.area
            )
            annotations.append(annotation)
            
        return annotations