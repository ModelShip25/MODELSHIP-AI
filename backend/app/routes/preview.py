# app/routes/preview.py
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, FileResponse

from ..core.utils import create_success_response, create_error_response
from ..models.annotation import Annotation
from ..services.preview import PreviewService, PreviewError

router = APIRouter()


def get_preview_service() -> PreviewService:
    """Dependency to get preview service instance."""
    return PreviewService()


@router.get("/{image_id}")
async def get_preview(
    image_id: str,
    show_labels: bool = Query(True, description="Show class labels on boxes"),
    show_scores: bool = Query(True, description="Show confidence scores"),
    min_score: Optional[float] = Query(0.0, description="Filter boxes below this confidence"),
    preview_service: PreviewService = Depends(get_preview_service)
):
    """
    Get a preview image with drawn bounding boxes.
    
    Args:
        image_id: ID of the image to preview
        show_labels: Whether to draw class labels
        show_scores: Whether to show confidence scores
        min_score: Minimum confidence score to show (0.0-1.0)
        preview_service: PreviewService instance
        
    Returns:
        Preview image file with drawn annotations
    """
    try:
        if min_score is not None and not (0.0 <= min_score <= 1.0):
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    message="Minimum score must be between 0.0 and 1.0"
                )
            )

        # Generate preview
        preview_path = await preview_service.generate_preview(
            image_id=image_id,
            show_labels=show_labels,
            show_confidence=show_scores,
            min_confidence=min_score or 0.0
        )
        
        # Return the image file
        return FileResponse(
            preview_path,
            media_type="image/png",
            filename=f"preview_{image_id}.png"
        )
        
    except PreviewError as pe:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="Failed to generate preview",
                details={"error": str(pe)}
            )
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="Internal server error",
                details={"error": str(e)}
            )
        )


@router.post("/{image_id}/edit")
async def update_preview(
    image_id: str,
    annotations: List[Annotation],
    preview_service: PreviewService = Depends(get_preview_service)
):
    """
    Update preview with edited annotations.
    
    Args:
        image_id: ID of the image to update
        annotations: List of updated annotations
        preview_service: PreviewService instance
        
    Returns:
        Updated preview image path and metadata
    """
    try:
        # Generate updated preview
        preview_result = await preview_service.update_preview(
            image_id=image_id,
            annotations=annotations
        )
        
        return create_success_response(
            message="Preview updated successfully",
            data=preview_result
        )
        
    except PreviewError as pe:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="Failed to update preview",
                details={"error": str(pe)}
            )
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="Internal server error",
                details={"error": str(e)}
            )
        )


@router.get("/{image_id}/metadata")
async def get_preview_metadata(
    image_id: str,
    preview_service: PreviewService = Depends(get_preview_service)
):
    """
    Get metadata about a preview image.
    
    Args:
        image_id: ID of the image
        preview_service: PreviewService instance
        
    Returns:
        Preview metadata including:
        - Original image dimensions
        - Number of annotations
        - Last update timestamp
        - Preview settings
    """
    try:
        metadata = await preview_service.get_preview_metadata(image_id)
        
        return create_success_response(
            message="Preview metadata retrieved successfully",
            data=metadata
        )
        
    except PreviewError as pe:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="Failed to get preview metadata",
                details={"error": str(pe)}
            )
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="Internal server error",
                details={"error": str(e)}
            )
        ) 