# app/services/labeling.py
import logging
from typing import Dict, List, Optional
import uuid
from datetime import datetime

from ..pipeline.detector import YOLOXDetector
from ..pipeline.sahi_wrapper import SAHIWrapper, SliceConfig
from ..pipeline.config import config
from ..storage.image_store import ImageStore
from ..models.annotation import Annotation, BoundingBox
from ..core.utils import create_success_response, create_error_response

logger = logging.getLogger(__name__)


class LabelingError(Exception):
    """Custom exception for labeling service errors."""
    pass


class LabelingService:
    """Service to coordinate SAHI + YOLOX labeling pipeline."""
    
    def __init__(self):
        """Initialize labeling service with YOLOX detector and SAHI predictor."""
        try:
            self.config = config
            self.detector = YOLOXDetector(
                model_path=self.config.model_path,
                conf_thresh=self.config.CONF_THRESH,
                nms_thresh=self.config.NMS_THRESH,
                input_size=self.config.INPUT_SIZE
            )
            self.predictor = SAHIWrapper(
                detector=self.detector,
                slice_config=SliceConfig(
                    slice_height=self.config.SLICE_HEIGHT,
                    slice_width=self.config.SLICE_WIDTH,
                    overlap_height_ratio=self.config.OVERLAP_HEIGHT_RATIO,
                    overlap_width_ratio=self.config.OVERLAP_WIDTH_RATIO,
                    auto_slice_resolution=self.config.AUTO_SLICE_RESOLUTION
                )
            )
            self.image_store = ImageStore()
            self._jobs = {}  # In-memory job storage
            
        except Exception as e:
            logger.error(f"Failed to initialize labeling service: {str(e)}")
            raise LabelingError(f"Service initialization failed: {str(e)}")

    async def process_batch(
        self,
        image_ids: List[str],
        confidence_threshold: Optional[float] = None
    ) -> Dict:
        """
        Process a batch of images through the SAHI + YOLOX pipeline.
        
        Args:
            image_ids: List of image IDs to process
            confidence_threshold: Optional override for model confidence threshold
            
        Returns:
            Dict containing:
            - job_id: Unique identifier for this labeling job
            - annotations: List of detected objects with bounding boxes
            - stats: Processing statistics and metrics
        """
        try:
            job_id = str(uuid.uuid4())
            self._jobs[job_id] = {
                "status": "processing",
                "start_time": datetime.utcnow(),
                "total_images": len(image_ids),
                "processed_images": 0,
                "annotations": [],
                "errors": []
            }

            # Update confidence threshold if provided
            if confidence_threshold is not None:
                self.detector.conf_thresh = confidence_threshold

            annotations = []
            processing_stats = {
                "total_objects": 0,
                "processing_time": 0,
                "average_confidence": 0.0
            }

            for image_id in image_ids:
                try:
                    # Get image path
                    image_path = await self.image_store.get_image_path(image_id)
                    
                    # Run SAHI detection
                    import cv2
                    image = cv2.imread(str(image_path))
                    predictions = await self.predictor.detect(image)
                    
                    # Add image_id to annotations
                    for annotation in predictions:
                        annotation.image_id = image_id
                    
                    annotations.extend(predictions)
                    
                    # Update statistics
                    processing_stats["total_objects"] += len(predictions)
                    processing_stats["average_confidence"] += sum(
                        ann.confidence for ann in predictions
                    )
                    
                    # Update job status
                    self._jobs[job_id]["processed_images"] += 1
                    
                except Exception as e:
                    error_msg = f"Failed to process image {image_id}: {str(e)}"
                    logger.error(error_msg)
                    self._jobs[job_id]["errors"].append(error_msg)

            # Finalize statistics
            if processing_stats["total_objects"] > 0:
                processing_stats["average_confidence"] /= processing_stats["total_objects"]
            
            processing_stats["processing_time"] = (
                datetime.utcnow() - self._jobs[job_id]["start_time"]
            ).total_seconds()

            # Update job completion
            self._jobs[job_id].update({
                "status": "completed",
                "end_time": datetime.utcnow(),
                "annotations": annotations,
                "stats": processing_stats
            })

            return {
                "job_id": job_id,
                "annotations": annotations,
                "stats": processing_stats
            }

        except Exception as e:
            error_msg = f"Batch processing failed: {str(e)}"
            logger.error(error_msg)
            if job_id in self._jobs:
                self._jobs[job_id].update({
                    "status": "failed",
                    "error": error_msg
                })
            raise LabelingError(error_msg)

    async def get_job_status(self, job_id: str) -> Dict:
        """Get status and results of a labeling job."""
        try:
            if job_id not in self._jobs:
                raise LabelingError(f"Job {job_id} not found")
                
            return self._jobs[job_id]
            
        except Exception as e:
            logger.error(f"Failed to get job status: {str(e)}")
            raise LabelingError(f"Failed to get job status: {str(e)}")

    async def get_model_config(self) -> Dict:
        """Get current model and SAHI configuration."""
        try:
            return {
                "model_path": str(self.config.model_path),
                "confidence_threshold": self.config.CONF_THRESH,
                "nms_threshold": self.config.NMS_THRESH,
                "input_size": self.config.INPUT_SIZE,
                "slice_height": self.config.SLICE_HEIGHT,
                "slice_width": self.config.SLICE_WIDTH,
                "overlap_height_ratio": self.config.OVERLAP_HEIGHT_RATIO,
                "overlap_width_ratio": self.config.OVERLAP_WIDTH_RATIO,
                "classes": self.config.CLASSES
            }
        except Exception as e:
            logger.error(f"Failed to get model config: {str(e)}")
            raise LabelingError(f"Failed to get model configuration: {str(e)}")

    def _convert_predictions(
        self,
        predictions: List[Dict],
        image_id: str
    ) -> List[Annotation]:
        """Convert SAHI predictions to annotation objects."""
        annotations = []
        
        for pred in predictions:
            try:
                # Create bounding box
                bbox = BoundingBox(
                    x_min=pred["bbox"]["x_min"],
                    y_min=pred["bbox"]["y_min"],
                    x_max=pred["bbox"]["x_max"],
                    y_max=pred["bbox"]["y_max"]
                )
                
                # Create annotation
                annotation = Annotation(
                    id=str(uuid.uuid4()),
                    image_id=image_id,
                    class_id=pred["category_id"],
                    class_name=pred["category_name"],
                    confidence=pred["score"],
                    bbox=bbox,
                    area=bbox.area,
                    source="sahi_yolox"
                )
                
                annotations.append(annotation)
                
            except Exception as e:
                logger.warning(f"Failed to convert prediction: {str(e)}")
                
        return annotations 