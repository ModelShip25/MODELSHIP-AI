# app/routes/label.py
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import JSONResponse

from ..core.utils import create_success_response, create_error_response
from ..models.annotation import Annotation
from ..services.labeling import LabelingService, LabelingError
from ..pipeline.config import ModelConfig

router = APIRouter()


def get_labeling_service() -> LabelingService:
    """Dependency to get labeling service instance."""
    return LabelingService()


@router.post("/batch", response_model=dict)
async def label_images(
    image_ids: List[str] = Body(..., description="List of image IDs to label"),
    confidence_threshold: Optional[float] = Body(0.5, description="Minimum confidence score for detections"),
    labeling_service: LabelingService = Depends(get_labeling_service)
):
    """
    Process a batch of images through the SAHI + YOLOX pipeline.
    
    Args:
        image_ids: List of image IDs to process
        confidence_threshold: Minimum confidence score (0.0-1.0)
        labeling_service: LabelingService instance
        
    Returns:
        Dict containing:
        - job_id: Unique identifier for this labeling job
        - total_images: Number of images processed
        - total_annotations: Number of objects detected
        - annotations: List of annotations with bounding boxes
        - processing_stats: Pipeline performance metrics
    """
    try:
        if not image_ids:
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    message="No image IDs provided"
                )
            )

        if not 0.0 <= confidence_threshold <= 1.0:
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    message="Confidence threshold must be between 0.0 and 1.0"
                )
            )

        # Process images through pipeline
        labeling_result = await labeling_service.process_batch(
            image_ids=image_ids,
            confidence_threshold=confidence_threshold
        )
        
        # Prepare response data
        response_data = {
            "job_id": labeling_result["job_id"],
            "total_images": len(image_ids),
            "total_annotations": len(labeling_result["annotations"]),
            "annotations": labeling_result["annotations"],
            "processing_stats": labeling_result["stats"]
        }
        
        return create_success_response(
            message=f"Successfully labeled {len(image_ids)} images. Found {response_data['total_annotations']} objects.",
            data=response_data
        )
        
    except LabelingError as le:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="Labeling pipeline failed",
                error=str(le)
            )
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="Failed to process images",
                error=str(e)
            )
        )


@router.get("/job/{job_id}")
async def get_job_status(
    job_id: str,
    labeling_service: LabelingService = Depends(get_labeling_service)
):
    """
    Get status and results of a labeling job.
    
    Args:
        job_id: Unique identifier for the labeling job
        labeling_service: LabelingService instance
    """
    try:
        job_status = await labeling_service.get_job_status(job_id)
        
        return create_success_response(
            message=f"Job status: {job_status['status']}",
            data=job_status
        )
        
    except LabelingError as le:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="Failed to get job status",
                error=str(le)
            )
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="Internal server error",
                error=str(e)
            )
        )


@router.get("/config")
async def get_model_config(
    labeling_service: LabelingService = Depends(get_labeling_service)
):
    """
    Get current model and SAHI configuration.
    """
    try:
        config = await labeling_service.get_model_config()
        
        return create_success_response(
            message="Current model configuration",
            data=config
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="Failed to get model configuration",
                error=str(e)
            )
        ) 