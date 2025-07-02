# app/routes/clean.py
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import JSONResponse

from ..core.utils import create_success_response, create_error_response
from ..models.image import ImageMetadata
from ..services.cleaning import ImageCleaner, CleaningError

router = APIRouter()


def get_image_cleaner() -> ImageCleaner:
    """Dependency to get image cleaner instance."""
    return ImageCleaner()


@router.post("/batch", response_model=dict)
async def clean_image_batch(
    image_ids: List[str] = Body(..., description="List of image IDs to process"),
    cleaner: ImageCleaner = Depends(get_image_cleaner)
):
    """
    Process a batch of uploaded images to remove duplicates.
    
    Args:
        image_ids: List of image IDs to process
        cleaner: ImageCleaner service instance
        
    Returns:
        Dict containing:
        - original_count: Number of images before cleaning
        - cleaned_count: Number of unique images after cleaning
        - duplicate_count: Number of duplicates found
        - unique_images: List of unique image IDs
        - duplicate_groups: List of duplicate image groups
    """
    try:
        if not image_ids:
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    message="No image IDs provided"
                )
            )

        # Process images and find duplicates
        cleaning_result = await cleaner.process_batch(image_ids)
        
        # Prepare response data
        response_data = {
            "original_count": len(image_ids),
            "cleaned_count": len(cleaning_result["unique_images"]),
            "duplicate_count": len(image_ids) - len(cleaning_result["unique_images"]),
            "unique_images": cleaning_result["unique_images"],
            "duplicate_groups": cleaning_result["duplicate_groups"]
        }
        
        return create_success_response(
            message=f"Successfully processed {len(image_ids)} images. Found {response_data['duplicate_count']} duplicates.",
            data=response_data
        )
        
    except CleaningError as ce:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="Image cleaning failed",
                error=str(ce)
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


@router.post("/validate", response_model=dict)
async def validate_images(
    image_ids: List[str] = Body(..., description="List of image IDs to validate"),
    cleaner: ImageCleaner = Depends(get_image_cleaner)
):
    """
    Validate a batch of images for format and content issues.
    
    Args:
        image_ids: List of image IDs to validate
        cleaner: ImageCleaner service instance
        
    Returns:
        Dict containing:
        - valid_images: List of valid image IDs
        - invalid_images: Dict of invalid image IDs with their issues
        - validation_summary: Summary of validation results
    """
    try:
        if not image_ids:
            return JSONResponse(
                status_code=400,
                content=create_error_response(
                    message="No image IDs provided"
                )
            )

        # Validate images
        validation_result = await cleaner.validate_images(image_ids)
        
        # Prepare response data
        response_data = {
            "total_images": len(image_ids),
            "valid_count": len(validation_result["valid_images"]),
            "invalid_count": len(validation_result["invalid_images"]),
            "valid_images": validation_result["valid_images"],
            "invalid_images": validation_result["invalid_images"],
            "validation_summary": validation_result["summary"]
        }
        
        return create_success_response(
            message=f"Validation complete. {response_data['valid_count']} valid, {response_data['invalid_count']} invalid images.",
            data=response_data
        )
        
    except CleaningError as ce:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                message="Image validation failed",
                error=str(ce)
            )
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="Failed to validate images",
                error=str(e)
            )
        )


@router.get("/status")
async def cleaning_status(
    cleaner: ImageCleaner = Depends(get_image_cleaner)
):
    """
    Get cleaning service status and statistics.
    """
    try:
        status_info = await cleaner.get_service_stats()
        
        return create_success_response(
            message="Cleaning service is operational",
            data=status_info
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                message="Failed to get cleaning status",
                error=str(e)
            )
        ) 