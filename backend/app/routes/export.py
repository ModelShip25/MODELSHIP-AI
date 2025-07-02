# app/routes/export.py
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from enum import Enum

from ..core.utils import create_success_response, create_error_response
from ..services.export import ExportService, ExportError, ExportFormat

router = APIRouter()


class ExportType(str, Enum):
    """Supported export format types."""
    YOLO = "yolo"
    COCO = "coco"
    CSV = "csv"
    ZIP = "zip"


def get_export_service() -> ExportService:
    """Dependency to get export service instance."""
    return ExportService()


@router.post("/{export_type}")
async def export_dataset(
    export_type: ExportType,
    image_ids: List[str],
    background_tasks: BackgroundTasks,
    include_images: bool = Query(False, description="Include original images in export"),
    include_previews: bool = Query(False, description="Include preview images in export"),
    min_confidence: Optional[float] = Query(0.0, description="Minimum confidence threshold for annotations"),
    export_service: ExportService = Depends(get_export_service)
):
    """
    Generate dataset export in specified format.
    
    Args:
        export_type: Format to export (YOLO, COCO, CSV, ZIP)
        image_ids: List of image IDs to export
        include_images: Whether to include original images
        include_previews: Whether to include preview images
        min_confidence: Minimum confidence threshold for annotations
        background_tasks: FastAPI background tasks
        export_service: ExportService instance
        
    Returns:
        Either direct file download or job ID for large exports
    """
    try:
        if not image_ids:
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    message="No image IDs provided"
                )
            )

        if min_confidence is not None and not (0.0 <= min_confidence <= 1.0):
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    message="Minimum confidence must be between 0.0 and 1.0"
                )
            )

        # Start export process
        export_result = await export_service.create_export(
            format=ExportFormat[export_type.upper()],
            image_ids=image_ids,
            include_images=include_images,
            include_previews=include_previews,
            min_confidence=min_confidence or 0.0
        )
        
        # For small exports, return direct download
        if export_result.get("ready", False):
            return FileResponse(
                export_result["file_path"],
                filename=export_result["filename"],
                media_type=export_result["media_type"]
            )
        
        # For large exports, return job ID and schedule cleanup
        background_tasks.add_task(
            export_service.cleanup_export,
            export_result["job_id"]
        )
        
        return create_success_response(
            message="Export started successfully",
            data={
                "job_id": export_result["job_id"],
                "status": "processing",
                "estimated_size": export_result["estimated_size"]
            }
        )
        
    except ExportError as ee:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="Export failed",
                details={"error": str(ee)}
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


@router.get("/download/{job_id}")
async def download_export(
    job_id: str,
    export_service: ExportService = Depends(get_export_service)
):
    """
    Download a completed export by job ID.
    
    Args:
        job_id: Export job identifier
        export_service: ExportService instance
    """
    try:
        # Get export status
        export_status = await export_service.get_export_status(job_id)
        
        if export_status["status"] != "completed":
            return create_success_response(
                message=f"Export status: {export_status['status']}",
                data=export_status
            )
            
        # Stream the file
        return FileResponse(
            export_status["file_path"],
            filename=export_status["filename"],
            media_type=export_status["media_type"]
        )
        
    except ExportError as ee:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="Failed to download export",
                details={"error": str(ee)}
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


@router.get("/status/{job_id}")
async def get_export_status(
    job_id: str,
    export_service: ExportService = Depends(get_export_service)
):
    """
    Check status of an export job.
    
    Args:
        job_id: Export job identifier
        export_service: ExportService instance
    """
    try:
        status = await export_service.get_export_status(job_id)
        
        return create_success_response(
            message=f"Export status: {status['status']}",
            data=status
        )
        
    except ExportError as ee:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="Failed to get export status",
                details={"error": str(ee)}
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