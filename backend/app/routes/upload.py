# app/routes/upload.py
import logging
from typing import List
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.utils import generate_unique_id, format_file_size, validate_image_file_upload, validate_image_content, create_success_response, create_error_response, create_validation_response
from app.models.image import (
    ImageUploadResponse, 
    ImageValidationError, 
    BatchUploadResponse
)
from app.storage.image_store import ImageStore, ImageStoreError

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency injection for image store
def get_image_store() -> ImageStore:
    """Dependency to get image store instance."""
    return ImageStore()


@router.post("/", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload a single image file.
    
    Accepts: JPG, JPEG, PNG, GIF files
    Returns: Image metadata with file path and ID
    """
    try:
        # Validate file metadata
        validation_result = validate_image_file_upload(file)
        if not validation_result["valid"]:
            return JSONResponse(
                status_code=400,
                content=create_validation_response(
                    errors=validation_result["errors"]
                )
            )
        
        # Read file content for validation
        file_content = await file.read()
        
        # Validate actual image content
        content_validation = validate_image_content(file_content)
        if not content_validation["valid"]:
            return JSONResponse(
                status_code=400,
                content=create_validation_response(
                    errors=content_validation["errors"]
                )
            )
        
        # Reset file pointer for saving
        file.file.seek(0)
        
        # Save image using image store
        saved_image = await get_image_store().save_image(file)
        
        # Return success response
        return create_success_response(
            message="Image uploaded successfully",
            data=saved_image
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="Failed to upload image",
                details={"error": str(e)}
            )
        )


@router.post("/batch", response_model=BatchUploadResponse)
async def upload_batch(files: List[UploadFile] = File(...)):
    """
    Upload multiple image files in batch.
    
    Accepts: Multiple JPG, JPEG, PNG, GIF files
    Returns: Batch upload results with success/failure details
    """
    try:
        if len(files) > 50:  # Limit batch size
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    message="Batch size too large. Maximum 50 files allowed."
                )
            )
        
        successful_uploads = []
        failed_uploads = []
        
        for file in files:
            try:
                # Validate each file
                validation_result = validate_image_file_upload(file)
                if not validation_result["valid"]:
                    failed_uploads.append({
                        "filename": file.filename,
                        "errors": validation_result["errors"]   
                    })
                    continue
                
                # Read and validate content
                file_content = await file.read()
                content_validation = validate_image_content(file_content)
                if not content_validation["valid"]:
                    failed_uploads.append({
                        "filename": file.filename,
                        "errors": content_validation["errors"]
                    })
                    continue
                
                # Reset file pointer and save
                file.file.seek(0)
                saved_image = await get_image_store().save_image(file)
                successful_uploads.append(saved_image)
                
            except Exception as e:
                failed_uploads.append({
                    "filename": file.filename,
                    "errors": [f"Upload failed: {str(e)}"]
                })
        
        # Prepare batch response
        batch_data = {
            "total_files": len(files),
            "successful_uploads": len(successful_uploads),
            "failed_uploads": len(failed_uploads),
            "uploaded_images": successful_uploads,
            "failed_files": failed_uploads
        }
        
        # Determine response status
        if len(successful_uploads) == 0:
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    message="All uploads failed",
                    details=batch_data
                )
            )
        elif len(failed_uploads) > 0:
            return JSONResponse(
                status_code=207,  # Multi-status
                content=create_success_response(
                    message=f"Batch upload completed: {len(successful_uploads)} successful, {len(failed_uploads)} failed",
                    data=batch_data
                )
            )
        else:
            return create_success_response(
                message="All files uploaded successfully",
                data=batch_data
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="Batch upload failed",
                details={"error": str(e)}
            )
        )


@router.get("/status")
async def upload_status():
    """
    Get upload service status and configuration.
    """
    try:
        status_info = await get_image_store().get_storage_info()
        
        return create_success_response(
            message="Upload service is operational",
            data=status_info
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="Failed to get upload status",
                details={"error": str(e)}
            )
        )


@router.get(
    "/upload/stats",
    summary="Get upload statistics",
    description="Get statistics about uploaded images and storage usage."
)
async def get_upload_stats(
    image_store: ImageStore = Depends(get_image_store)
) -> dict:
    """
    Get statistics about uploads and storage.
    
    Args:
        image_store: Image storage service (injected)
        
    Returns:
        Dictionary with upload and storage statistics
    """
    try:
        stats = image_store.get_storage_stats()
        
        # Add configuration info
        stats.update({
            "max_file_size": settings.MAX_FILE_SIZE,
            "max_file_size_formatted": format_file_size(settings.MAX_FILE_SIZE),
            "allowed_extensions": list(settings.get_allowed_extensions_set()),
            "storage_directory": settings.STORAGE_DIR
        })
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting upload stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving upload statistics"
        )


@router.delete(
    "/upload/{filename}",
    summary="Delete uploaded image",
    description="Delete a specific uploaded image file."
)
async def delete_uploaded_image(
    filename: str,
    image_store: ImageStore = Depends(get_image_store)
) -> dict:
    """
    Delete an uploaded image file.
    
    Args:
        filename: Name of the file to delete
        image_store: Image storage service (injected)
        
    Returns:
        Confirmation of deletion
        
    Raises:
        HTTPException: If file doesn't exist or deletion fails
    """
    logger.info(f"Attempting to delete image: {filename}")
    
    try:
        if not image_store.image_exists(filename):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image not found: {filename}"
            )
        
        success = await image_store.delete_image(filename)
        
        if success:
            logger.info(f"Successfully deleted image: {filename}")
            return {"message": f"Image deleted successfully: {filename}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete image: {filename}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting image {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during deletion"
        )
