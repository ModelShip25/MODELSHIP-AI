# app/pipeline/sahi_wrapper.py
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import cv2
import uuid

from sahi.slicing import slice_image
from sahi.prediction import ObjectPrediction
from sahi.postprocess.combine import PostprocessPredictions

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
    auto_slice_resolution: bool = True


class SAHIError(Exception):
    """Custom exception for SAHI processing errors."""
    pass


class SAHIWrapper:
    """Wrapper for SAHI sliced inference with YOLOX detector."""
    
    def __init__(
        self,
        detector: YOLOXDetector,
        slice_config: Optional[SliceConfig] = None,
        postprocess_type: str = "NMM",
        postprocess_match_threshold: float = 0.5,
        postprocess_match_metric: str = "IOU"
    ):
        """
        Initialize SAHI wrapper.
        
        Args:
            detector: YOLOX detector instance
            slice_config: Configuration for image slicing
            postprocess_type: Type of postprocessing ('NMM' or 'NMS')
            postprocess_match_threshold: Threshold for matching predictions
            postprocess_match_metric: Metric for matching ('IOU' or 'IOS')
        """
        self.detector = detector
        self.slice_config = slice_config or SliceConfig()
        self.postprocess_type = postprocess_type
        self.postprocess_match_threshold = postprocess_match_threshold
        self.postprocess_match_metric = postprocess_match_metric
    
    async def detect(
        self,
        image: np.ndarray,
        conf_thresh: Optional[float] = None,
        nms_thresh: Optional[float] = None
    ) -> List[Annotation]:
        """
        Run sliced detection on an image.
        
        Args:
            image: BGR image as numpy array
            conf_thresh: Optional override for confidence threshold
            nms_thresh: Optional override for NMS threshold
            
        Returns:
            List of Annotation objects
        """
        try:
            # Calculate optimal slice size if auto_slice_resolution is enabled
            if self.slice_config.auto_slice_resolution:
                slice_size = self._calculate_optimal_slice_size(image.shape[:2])
                self.slice_config.slice_height = slice_size[0]
                self.slice_config.slice_width = slice_size[1]
            
            # Get image slices
            slices = self._get_slices(image)
            logger.info(f"Created {len(slices)} slices")
            
            # Process each slice
            all_predictions = []
            for slice_data in slices:
                # Get slice image
                slice_image = image[
                    slice_data["y_min"]:slice_data["y_max"],
                    slice_data["x_min"]:slice_data["x_max"]
                ]
                
                # Run detection on slice
                predictions = self.detector.detect(
                    slice_image,
                    conf_thresh=conf_thresh,
                    nms_thresh=nms_thresh
                )
                
                # Convert predictions to SAHI format and adjust coordinates
                for pred in predictions:
                    bbox = pred["bbox"]
                    # Adjust coordinates to full image space
                    full_image_bbox = [
                        bbox[0] + slice_data["x_min"],
                        bbox[1] + slice_data["y_min"],
                        bbox[2] + slice_data["x_min"],
                        bbox[3] + slice_data["y_min"]
                    ]
                    
                    object_pred = ObjectPrediction(
                        bbox=full_image_bbox,
                        category_id=pred["class_id"],
                        category_name=pred["class_name"],
                        score=pred["confidence"]
                    )
                    all_predictions.append(object_pred)
            
            # Postprocess predictions
            postprocess = PostprocessPredictions(
                match_threshold=self.postprocess_match_threshold,
                match_metric=self.postprocess_match_metric
            )
            
            merged_predictions = postprocess(all_predictions)
            
            # Convert to Annotation format
            annotations = []
            for i, pred in enumerate(merged_predictions):
                bbox = pred.bbox.to_xyxy()
                bbox_obj = BoundingBox(
                    x_min=bbox[0],
                    y_min=bbox[1], 
                    x_max=bbox[2],
                    y_max=bbox[3]
                )
                
                annotation = Annotation(
                    id=str(uuid.uuid4()),
                    image_id="",  # Will be set by the service
                    class_id=pred.category_id,
                    class_name=pred.category_name,
                    confidence=pred.score,
                    bbox=bbox_obj,
                    area=(bbox_obj.x_max - bbox_obj.x_min) * (bbox_obj.y_max - bbox_obj.y_min),
                    source="sahi_yolox"
                )
                annotations.append(annotation)
            
            logger.info(
                f"Found {len(annotations)} objects after merging "
                f"predictions from {len(slices)} slices"
            )
            
            return annotations
            
        except Exception as e:
            error_msg = f"SAHI processing failed: {str(e)}"
            logger.error(error_msg)
            raise SAHIError(error_msg)
    
    def _get_slices(self, image: np.ndarray) -> List[Dict]:
        """Get slice coordinates for an image."""
        height, width = image.shape[:2]
        
        # Calculate slices manually since SAHI slice_image expects PIL Image or path
        slices = []
        
        # Calculate number of slices
        slice_h = self.slice_config.slice_height
        slice_w = self.slice_config.slice_width
        overlap_h = int(slice_h * self.slice_config.overlap_height_ratio)
        overlap_w = int(slice_w * self.slice_config.overlap_width_ratio)
        
        # Calculate step sizes
        step_h = slice_h - overlap_h
        step_w = slice_w - overlap_w
        
        y = 0
        while y < height:
            x = 0
            while x < width:
                # Calculate slice bounds
                y_max = min(y + slice_h, height)
                x_max = min(x + slice_w, width)
                
                # Ensure minimum slice size
                if (y_max - y) >= slice_h // 2 and (x_max - x) >= slice_w // 2:
                    slices.append({
                        "x_min": x,
                        "y_min": y,
                        "x_max": x_max,
                        "y_max": y_max
                    })
                
                # Move to next x position
                if x_max >= width:
                    break
                x += step_w
            
            # Move to next y position
            if y_max >= height:
                break
            y += step_h
        
        return slices
    
    def _calculate_optimal_slice_size(
        self,
        image_shape: Tuple[int, int],
        target_resolution: int = 640
    ) -> Tuple[int, int]:
        """
        Calculate optimal slice size based on image dimensions.
        
        Args:
            image_shape: Image dimensions (height, width)
            target_resolution: Target resolution for slices
            
        Returns:
            Tuple of (slice_height, slice_width)
        """
        height, width = image_shape
        
        # Calculate number of slices needed
        n_height = max(1, height // target_resolution)
        n_width = max(1, width // target_resolution)
        
        # Calculate slice size with overlap consideration
        slice_height = int(
            height / (
                n_height - (n_height - 1) * self.slice_config.overlap_height_ratio
            )
        )
        slice_width = int(
            width / (
                n_width - (n_width - 1) * self.slice_config.overlap_width_ratio
            )
        )
        
        return slice_height, slice_width