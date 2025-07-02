# app/pipeline/config.py
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import BaseSettings, Field
import json
import logging

logger = logging.getLogger(__name__)


class ModelConfig(BaseSettings):
    """Configuration for YOLOX model and pipeline settings."""
    
    # Model paths and files
    MODEL_DIR: Path = Field(
        default=Path("models"),
        description="Directory containing model files"
    )
    MODEL_FILE: str = Field(
        default="yolox_s.onnx",
        description="ONNX model filename"
    )
    CLASSES_FILE: str = Field(
        default="classes.json",
        description="JSON file containing class names"
    )
    
    # Model parameters
    INPUT_SIZE: Tuple[int, int] = Field(
        default=(640, 640),
        description="Model input size (width, height)"
    )
    CONF_THRESH: float = Field(
        default=0.3,
        description="Confidence threshold for detections"
    )
    NMS_THRESH: float = Field(
        default=0.45,
        description="Non-maximum suppression threshold"
    )
    
    # SAHI parameters
    SLICE_HEIGHT: int = Field(
        default=512,
        description="Height of image slices"
    )
    SLICE_WIDTH: int = Field(
        default=512,
        description="Width of image slices"
    )
    OVERLAP_HEIGHT_RATIO: float = Field(
        default=0.2,
        description="Vertical overlap ratio between slices"
    )
    OVERLAP_WIDTH_RATIO: float = Field(
        default=0.2,
        description="Horizontal overlap ratio between slices"
    )
    AUTO_SLICE_RESOLUTION: bool = Field(
        default=True,
        description="Automatically adjust slice size based on image"
    )
    
    # Postprocessing parameters
    POSTPROCESS_TYPE: str = Field(
        default="NMM",
        description="Type of postprocessing (NMM or NMS)"
    )
    POSTPROCESS_MATCH_THRESHOLD: float = Field(
        default=0.5,
        description="Threshold for matching predictions in postprocessing"
    )
    POSTPROCESS_MATCH_METRIC: str = Field(
        default="IOU",
        description="Metric for matching predictions (IOU or IOS)"
    )
    
    # Class mapping
    CLASSES: List[str] = Field(
        default=[],
        description="List of class names"
    )
    CLASS_COLORS: Dict[str, Tuple[int, int, int]] = Field(
        default={},
        description="Mapping of class names to BGR colors"
    )
    
    class Config:
        env_prefix = "MODELSHIP_"
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_classes()
        self._validate_paths()
    
    def _load_classes(self):
        """Load class names from JSON file if available."""
        try:
            classes_path = self.MODEL_DIR / self.CLASSES_FILE
            if classes_path.exists():
                with open(classes_path) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.CLASSES = data
                    elif isinstance(data, dict) and "classes" in data:
                        self.CLASSES = data["classes"]
                    
                    # Load colors if available
                    if isinstance(data, dict) and "colors" in data:
                        self.CLASS_COLORS = {
                            cls: tuple(color)
                            for cls, color in data["colors"].items()
                        }
                logger.info(f"Loaded {len(self.CLASSES)} classes")
            else:
                logger.warning(
                    f"Classes file not found: {classes_path}. "
                    "Using numeric class IDs."
                )
                
        except Exception as e:
            logger.error(f"Failed to load classes: {str(e)}")
            self.CLASSES = []
    
    def _validate_paths(self):
        """Validate and create necessary directories."""
        try:
            # Ensure model directory exists
            self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
            
            # Check model file
            model_path = self.MODEL_DIR / self.MODEL_FILE
            if not model_path.exists():
                logger.warning(
                    f"Model file not found: {model_path}. "
                    "Please download the model file."
                )
                
        except Exception as e:
            logger.error(f"Path validation failed: {str(e)}")
    
    @property
    def model_path(self) -> Path:
        """Get full path to model file."""
        return self.MODEL_DIR / self.MODEL_FILE
    
    @property
    def YOLOX_MODEL_PATH(self) -> Path:
        """Alias for model_path for backward compatibility."""
        return self.model_path
    
    def get_class_name(self, class_id: int) -> str:
        """Get class name for ID, falling back to string ID if not found."""
        try:
            return self.CLASSES[class_id]
        except (IndexError, TypeError):
            return str(class_id)
    
    def get_class_color(
        self,
        class_name: str,
        default: Tuple[int, int, int] = (0, 255, 0)
    ) -> Tuple[int, int, int]:
        """Get BGR color for class name, falling back to default if not found."""
        return self.CLASS_COLORS.get(class_name, default)


# Create global instance
config = ModelConfig()

# Example .env file:
"""
MODELSHIP_MODEL_DIR=models
MODELSHIP_MODEL_FILE=yolox_s.onnx
MODELSHIP_CLASSES_FILE=classes.json
MODELSHIP_CONF_THRESH=0.3
MODELSHIP_NMS_THRESH=0.45
MODELSHIP_SLICE_HEIGHT=512
MODELSHIP_SLICE_WIDTH=512
MODELSHIP_OVERLAP_HEIGHT_RATIO=0.2
MODELSHIP_OVERLAP_WIDTH_RATIO=0.2
MODELSHIP_AUTO_SLICE_RESOLUTION=true
MODELSHIP_POSTPROCESS_TYPE=NMM
MODELSHIP_POSTPROCESS_MATCH_THRESHOLD=0.5
MODELSHIP_POSTPROCESS_MATCH_METRIC=IOU
"""

# Example classes.json:
"""
{
    "classes": [
        "person",
        "bicycle",
        "car",
        ...
    ],
    "colors": {
        "person": [0, 255, 0],
        "bicycle": [255, 0, 0],
        "car": [0, 0, 255],
        ...
    }
}
""" 