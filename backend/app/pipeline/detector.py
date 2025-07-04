# app/pipeline/detector.py
import numpy as np
import cv2
import onnxruntime
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple, Union
import time

from .config import config

logger = logging.getLogger(__name__)


class DetectorError(Exception):
    """Custom exception for detector errors."""
    pass


class YOLOXDetector:
    """YOLOX object detector using ONNXRuntime."""
    
    def __init__(
        self,
        model_path: Union[str, Path],
        conf_thresh: float = 0.3,
        nms_thresh: float = 0.45,
        input_size: Tuple[int, int] = (640, 640)
    ):
        """
        Initialize YOLOX detector.
        
        Args:
            model_path: Path to ONNX model file
            conf_thresh: Confidence threshold for detections
            nms_thresh: Non-maximum suppression threshold
            input_size: Model input size (width, height)
        """
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise DetectorError(f"Model not found: {model_path}")
            
        self.conf_thresh = conf_thresh
        self.nms_thresh = nms_thresh
        self.input_size = input_size
        
        # Load model
        logger.info(f"Loading YOLOX model from {model_path}")
        try:
            self.session = onnxruntime.InferenceSession(
                str(model_path),
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )
            
            # Get model metadata
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            raise DetectorError(f"Failed to load model: {str(e)}")
    
    def detect(
        self,
        image: np.ndarray,
        conf_thresh: Optional[float] = None,
        nms_thresh: Optional[float] = None
    ) -> List[Dict]:
        """
        Run object detection on an image.
        
        Args:
            image: BGR image as numpy array
            conf_thresh: Optional override for confidence threshold
            nms_thresh: Optional override for NMS threshold
            
        Returns:
            List of detections, each a dict with:
            - bbox: [x_min, y_min, x_max, y_max]
            - confidence: Detection confidence
            - class_id: Class ID from model
            - class_name: Class name (if available)
        """
        try:
            start_time = time.time()
            
            # Preprocess image
            input_data = self._preprocess(image)
            
            # Run inference
            outputs = self.session.run(
                [self.output_name],
                {self.input_name: input_data}
            )[0]
            
            # Ensure outputs is a numpy array
            if not isinstance(outputs, np.ndarray):
                outputs = np.array(outputs)
            
            # Postprocess detections
            predictions = self._postprocess(
                outputs,
                image.shape[:2],  # Original (height, width)
                conf_thresh or self.conf_thresh,
                nms_thresh or self.nms_thresh
            )
            
            inference_time = time.time() - start_time
            logger.debug(f"Detection took {inference_time:.3f}s")
            
            return predictions
            
        except Exception as e:
            raise DetectorError(f"Detection failed: {str(e)}")
    
    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for model input."""
        # Resize
        resized = cv2.resize(
            image,
            self.input_size,
            interpolation=cv2.INTER_LINEAR
        )
        
        # BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize to [0, 1]
        normalized = rgb.astype(np.float32) / 255.0
        
        # HWC to NCHW format
        transposed = np.transpose(normalized, (2, 0, 1))
        
        # Add batch dimension
        batched = np.expand_dims(transposed, axis=0)
        
        return batched
    
    def _postprocess(
        self,
        outputs: np.ndarray,
        original_shape: Tuple[int, int],
        conf_thresh: float,
        nms_thresh: float
    ) -> List[Dict]:
        """
        Postprocess raw model outputs.
        
        Args:
            outputs: Raw model outputs
            original_shape: Original image (height, width)
            conf_thresh: Confidence threshold
            nms_thresh: NMS threshold
            
        Returns:
            List of processed detections
        """
        predictions = []
        
        # Get predictions above threshold
        scores = outputs[..., 4:5] * outputs[..., 5:]  # cls conf * obj conf
        boxes = outputs[..., :4]
        
        # Filter by confidence
        mask = scores.max(1) > conf_thresh
        boxes = boxes[mask]
        scores = scores[mask]
        
        if boxes.shape[0] == 0:
            return predictions
            
        # Get class predictions
        class_ids = np.argmax(scores, axis=1)
        confidences = scores.max(1)
        
        # Convert boxes to corners (xywh -> xyxy)
        boxes = self._xywh2xyxy(boxes)
        
        # Scale boxes to original image size
        scale_x = original_shape[1] / self.input_size[0]
        scale_y = original_shape[0] / self.input_size[1]
        boxes[:, [0, 2]] *= scale_x
        boxes[:, [1, 3]] *= scale_y
        
        # Apply NMS
        indices = cv2.dnn.NMSBoxes(
            boxes.tolist(),
            confidences.tolist(),
            conf_thresh,
            nms_thresh
        )
        
        # Format predictions
        for idx in indices:
            idx = idx if isinstance(idx, int) else idx.item()
            predictions.append({
                "bbox": boxes[idx].tolist(),
                "confidence": float(confidences[idx]),
                "class_id": int(class_ids[idx]),
                "class_name": config.get_class_name(class_ids[idx])
            })
        
        return predictions
    
    @staticmethod
    def _xywh2xyxy(boxes: np.ndarray) -> np.ndarray:
        """Convert boxes from (x, y, w, h) to (x1, y1, x2, y2) format."""
        xyxy = boxes.copy()
        xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2  # x1 = x - w/2
        xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2  # y1 = y - h/2
        xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2  # x2 = x + w/2
        xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2  # y2 = y + h/2
        return xyxy 