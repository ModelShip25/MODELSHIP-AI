# app/services/cleaning.py
import os
from typing import Dict, List, Set, Tuple
from PIL import Image
import imagehash
from collections import defaultdict
import logging
from pathlib import Path

from ..core.utils import get_file_hash, validate_image_content
from ..storage.image_store import ImageStore
from ..models.image import ImageMetadata

logger = logging.getLogger(__name__)


class CleaningError(Exception):
    """Custom exception for cleaning service errors."""
    pass


class ImageCleaner:
    """Service for detecting and removing duplicate images using perceptual hashing."""
    
    def __init__(self):
        self.image_store = ImageStore()
        # Configurable threshold for image similarity (0-64, lower = more similar)
        self.hash_threshold = 8  
        
    async def process_batch(
        self,
        image_ids: List[str]
    ) -> Dict:
        """
        Process a batch of images to find and group duplicates.
        
        Args:
            image_ids: List of image IDs to process
            
        Returns:
            Dict containing:
            - unique_images: List of unique image IDs
            - duplicate_groups: List of lists containing duplicate image IDs
        """
        try:
            # Get image paths from store
            image_paths = await self._get_image_paths(image_ids)
            
            # Calculate hashes for all images
            image_hashes = await self._calculate_image_hashes(image_paths)
            
            # Group similar images
            unique_images, duplicate_groups = self._find_duplicates(image_hashes)
            
            return {
                "unique_images": list(unique_images),
                "duplicate_groups": duplicate_groups
            }
            
        except Exception as e:
            logger.error(f"Failed to process batch: {str(e)}")
            raise CleaningError(f"Batch processing failed: {str(e)}")

    async def validate_images(
        self,
        image_ids: List[str]
    ) -> Dict:
        """
        Validate image format and content.
        
        Args:
            image_ids: List of image IDs to validate
            
        Returns:
            Dict containing:
            - valid_images: List of valid image IDs
            - invalid_images: Dict mapping invalid image IDs to their issues
            - summary: Validation statistics
        """
        try:
            valid_images = []
            invalid_images = {}
            
            for image_id in image_ids:
                try:
                    # Get image path
                    image_path = await self.image_store.get_image_path(image_id)
                    
                    # Read image content
                    with open(image_path, 'rb') as f:
                        content = f.read()
                    
                    # Validate content
                    validation_result = validate_image_content(content)
                    
                    if validation_result["valid"]:
                        valid_images.append(image_id)
                    else:
                        invalid_images[image_id] = validation_result["errors"]
                        
                except Exception as e:
                    invalid_images[image_id] = [f"Validation failed: {str(e)}"]
            
            # Prepare summary
            summary = {
                "total_images": len(image_ids),
                "valid_count": len(valid_images),
                "invalid_count": len(invalid_images)
            }
            
            return {
                "valid_images": valid_images,
                "invalid_images": invalid_images,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Image validation failed: {str(e)}")
            raise CleaningError(f"Validation failed: {str(e)}")

    async def get_service_stats(self) -> Dict:
        """Get cleaning service statistics and status."""
        try:
            return {
                "status": "operational",
                "hash_threshold": self.hash_threshold,
                "supported_formats": ["jpg", "jpeg", "png", "gif"],
                "max_batch_size": 1000
            }
        except Exception as e:
            logger.error(f"Failed to get service stats: {str(e)}")
            raise CleaningError(f"Failed to get service statistics: {str(e)}")

    async def _get_image_paths(self, image_ids: List[str]) -> Dict[str, str]:
        """Get mapping of image IDs to their file paths."""
        paths = {}
        for image_id in image_ids:
            try:
                path = await self.image_store.get_image_path(image_id)
                paths[image_id] = path
            except Exception as e:
                logger.warning(f"Failed to get path for image {image_id}: {str(e)}")
        return paths

    async def _calculate_image_hashes(
        self,
        image_paths: Dict[str, str]
    ) -> Dict[str, Tuple[imagehash.ImageHash, str]]:
        """
        Calculate perceptual hashes for images.
        
        Returns dict mapping image IDs to tuples of (hash, file_path)
        """
        image_hashes = {}
        
        for image_id, path in image_paths.items():
            try:
                with Image.open(path) as img:
                    # Convert to RGB to handle all formats
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    # Calculate average hash
                    hash_value = imagehash.average_hash(img)
                    image_hashes[image_id] = (hash_value, path)
            except Exception as e:
                logger.warning(f"Failed to hash image {image_id}: {str(e)}")
                
        return image_hashes

    def _find_duplicates(
        self,
        image_hashes: Dict[str, Tuple[imagehash.ImageHash, str]]
    ) -> Tuple[Set[str], List[List[str]]]:
        """
        Find duplicate images using hash comparison.
        
        Returns:
            Tuple containing:
            - Set of unique image IDs
            - List of duplicate groups
        """
        # Track processed images and duplicates
        unique_images = set()
        duplicate_groups = []
        processed = set()
        
        for image_id, (hash1, path1) in image_hashes.items():
            if image_id in processed:
                continue
                
            # Find all similar images
            similar_images = []
            
            for other_id, (hash2, path2) in image_hashes.items():
                if other_id == image_id or other_id in processed:
                    continue
                    
                # Compare hashes
                if abs(hash1 - hash2) <= self.hash_threshold:
                    similar_images.append(other_id)
                    processed.add(other_id)
            
            if similar_images:
                # Add current image to duplicates
                similar_images.append(image_id)
                duplicate_groups.append(similar_images)
                processed.add(image_id)
            else:
                # Image is unique
                unique_images.add(image_id)
                processed.add(image_id)
        
        return unique_images, duplicate_groups 