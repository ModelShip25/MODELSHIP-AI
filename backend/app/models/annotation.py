from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class BoundingBox(BaseModel):
    """Base bounding box schema with absolute coordinates."""
    x_min: float = Field(..., description="Left coordinate in pixels", ge=0)
    y_min: float = Field(..., description="Top coordinate in pixels", ge=0) 
    x_max: float = Field(..., description="Right coordinate in pixels", gt=0)
    y_max: float = Field(..., description="Bottom coordinate in pixels", gt=0)
    
    @property
    def width(self) -> float:
        """Calculate width from coordinates."""
        return self.x_max - self.x_min
    
    @property
    def height(self) -> float:
        """Calculate height from coordinates."""
        return self.y_max - self.y_min
    
    @property
    def area(self) -> float:
        """Calculate area from coordinates."""
        return self.width * self.height
    
    @property
    def center_x(self) -> float:
        """Calculate center X coordinate."""
        return (self.x_min + self.x_max) / 2
    
    @property
    def center_y(self) -> float:
        """Calculate center Y coordinate."""
        return (self.y_min + self.y_max) / 2
    
    @classmethod
    def from_xywh(cls, x: float, y: float, width: float, height: float) -> "BoundingBox":
        """Create BoundingBox from x, y, width, height format."""
        return cls(
            x_min=x,
            y_min=y,
            x_max=x + width,
            y_max=y + height
        )
    
    def to_xywh(self) -> tuple[float, float, float, float]:
        """Convert to x, y, width, height format."""
        return (self.x_min, self.y_min, self.width, self.height)
    
    def to_xyxy(self) -> tuple[float, float, float, float]:
        """Convert to x_min, y_min, x_max, y_max format."""
        return (self.x_min, self.y_min, self.x_max, self.y_max)
    
    @validator("x_max", always=True)
    def validate_x_max(cls, v, values):
        """Ensure x_max > x_min."""
        if "x_min" in values and v <= values["x_min"]:
            raise ValueError("x_max must be greater than x_min")
        return v
    
    @validator("y_max", always=True)
    def validate_y_max(cls, v, values):
        """Ensure y_max > y_min."""
        if "y_min" in values and v <= values["y_min"]:
            raise ValueError("y_max must be greater than y_min")
        return v


class NormalizedBoundingBox(BaseModel):
    """Normalized bounding box for YOLO format (0-1 range)."""
    x_center: float = Field(..., description="Center X coordinate (normalized)", ge=0, le=1)
    y_center: float = Field(..., description="Center Y coordinate (normalized)", ge=0, le=1)
    width: float = Field(..., description="Width (normalized)", gt=0, le=1)
    height: float = Field(..., description="Height (normalized)", gt=0, le=1)


class Annotation(BaseModel):
    """Base annotation schema for object detection."""
    id: str = Field(..., description="Unique annotation identifier")
    image_id: str = Field(..., description="Associated image identifier")
    class_id: int = Field(..., description="Object class ID", ge=0)
    class_name: str = Field(..., description="Object class name")
    confidence: float = Field(..., description="Detection confidence score", ge=0, le=1)
    bbox: BoundingBox = Field(..., description="Bounding box coordinates")
    area: float = Field(..., description="Bounding box area in pixels", gt=0)
    source: str = Field(default="yolox", description="Detection source (model name)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class YOLOAnnotation(BaseModel):
    """YOLO format annotation schema."""
    class_id: int = Field(..., description="Object class ID", ge=0)
    bbox: NormalizedBoundingBox = Field(..., description="Normalized bounding box")
    confidence: Optional[float] = Field(None, description="Detection confidence", ge=0, le=1)
    
    def to_yolo_string(self) -> str:
        """Convert to YOLO format string: class_id x_center y_center width height"""
        bbox = self.bbox
        return f"{self.class_id} {bbox.x_center} {bbox.y_center} {bbox.width} {bbox.height}"


class COCOAnnotation(BaseModel):
    """COCO format annotation schema."""
    id: int = Field(..., description="Annotation ID", ge=1)
    image_id: int = Field(..., description="Image ID", ge=1)
    category_id: int = Field(..., description="Category ID", ge=1)
    bbox: List[float] = Field(..., description="Bounding box [x, y, width, height]")
    area: float = Field(..., description="Area of the bounding box", gt=0)
    iscrowd: int = Field(default=0, description="Is crowd annotation (0 or 1)")
    segmentation: List[List[float]] = Field(default_factory=list, description="Segmentation polygons")
    
    @validator("bbox")
    def validate_bbox(cls, v):
        """Validate COCO bbox format [x, y, width, height]."""
        if len(v) != 4:
            raise ValueError("COCO bbox must have exactly 4 values: [x, y, width, height]")
        if any(val < 0 for val in v):
            raise ValueError("COCO bbox values must be non-negative")
        if v[2] <= 0 or v[3] <= 0:
            raise ValueError("COCO bbox width and height must be positive")
        return v

    @classmethod
    def from_annotation(cls, ann: Annotation, annotation_id: int, category_id: int) -> "COCOAnnotation":
        """Convert from base Annotation to COCO format."""
        # Convert from x_min, y_min, x_max, y_max to x, y, width, height
        bbox = [
            ann.bbox.x_min,  # x
            ann.bbox.y_min,  # y
            ann.bbox.width,  # width
            ann.bbox.height  # height
        ]
        
        return cls(
            id=annotation_id,
            image_id=int(ann.image_id),  # COCO requires int IDs
            category_id=category_id,
            bbox=bbox,
            area=ann.area
        )


class AnnotationResponse(BaseModel):
    """Response schema for single annotation operations."""
    success: bool = Field(True, description="Operation success status")
    message: str = Field("Annotation processed successfully", description="Response message")
    data: Annotation = Field(..., description="Annotation data")


class AnnotationListResponse(BaseModel):
    """Response schema for multiple annotations."""
    success: bool = Field(True, description="Request success status")
    message: str = Field("Annotations retrieved successfully", description="Response message")
    data: List[Annotation] = Field(..., description="List of annotations")
    total: int = Field(..., description="Total number of annotations")
    image_id: str = Field(..., description="Associated image identifier")


class LabelingJobResponse(BaseModel):
    """Response schema for labeling job results."""
    success: bool = Field(True, description="Labeling job success status")
    message: str = Field(..., description="Labeling job summary")
    image_id: str = Field(..., description="Processed image identifier")
    annotations: List[Annotation] = Field(..., description="Generated annotations")
    annotation_count: int = Field(..., description="Number of annotations created")
    processing_time: float = Field(..., description="Processing time in seconds")
    model_info: Dict[str, Any] = Field(default_factory=dict, description="Model metadata")


class YOLOExport(BaseModel):
    """Schema for YOLO format export."""
    image_filename: str = Field(..., description="Image filename")
    annotations: List[YOLOAnnotation] = Field(..., description="YOLO format annotations")
    classes: Dict[int, str] = Field(..., description="Class ID to name mapping")
    
    def to_yolo_file_content(self) -> str:
        """Generate YOLO .txt file content."""
        lines = []
        for annotation in self.annotations:
            lines.append(annotation.to_yolo_string())
        return "\n".join(lines)


class COCOExport(BaseModel):
    """Schema for COCO format export."""
    info: Dict[str, Any] = Field(default_factory=dict, description="Dataset info")
    licenses: List[Dict[str, Any]] = Field(default_factory=list, description="License info")
    images: List[Dict[str, Any]] = Field(..., description="Image metadata")
    annotations: List[COCOAnnotation] = Field(..., description="COCO format annotations")
    categories: List[Dict[str, Any]] = Field(..., description="Category definitions")


class BatchLabelingResponse(BaseModel):
    """Response schema for batch labeling operations."""
    success: bool = Field(True, description="Batch labeling completion status")
    message: str = Field(..., description="Batch labeling summary")
    results: List[LabelingJobResponse] = Field(..., description="Individual labeling results")
    total_images: int = Field(..., description="Total images processed")
    total_annotations: int = Field(..., description="Total annotations generated")
    failed_images: List[str] = Field(default_factory=list, description="Failed image IDs")
    processing_time: float = Field(..., description="Total processing time in seconds")


class AnnotationStats(BaseModel):
    """Schema for annotation statistics."""
    success: bool = Field(True, description="Request success status")
    total_annotations: int = Field(..., description="Total number of annotations")
    annotations_by_class: Dict[str, int] = Field(..., description="Annotations count per class")
    average_confidence: float = Field(..., description="Average confidence score")
    images_with_annotations: int = Field(..., description="Number of images with annotations")
    last_updated: datetime = Field(..., description="Last annotation timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 