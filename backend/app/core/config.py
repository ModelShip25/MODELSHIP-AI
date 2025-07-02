# app/core/config.py
import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Production-ready configuration management using environment variables."""
    
    # API Settings
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "ModelShip")
    VERSION: str = os.getenv("VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Server Settings  
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Storage Settings
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "uploads")
    TEMP_DIR: str = os.getenv("TEMP_DIR", "temp")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "52428800"))  # 50MB default
    ALLOWED_EXTENSIONS: List[str] = os.getenv("ALLOWED_EXTENSIONS", ".jpg,.jpeg,.png,.bmp,.tiff,.webp").split(",")
    
    # Supabase Settings
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY") 
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "modelship-images")
    
    # Model & Pipeline Settings
    MODEL_PATH: str = os.getenv("MODEL_PATH", "models/yolox_s.onnx")
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
    NMS_THRESHOLD: float = float(os.getenv("NMS_THRESHOLD", "0.5"))
    
    # SAHI Settings
    SLICE_HEIGHT: int = int(os.getenv("SLICE_HEIGHT", "640"))
    SLICE_WIDTH: int = int(os.getenv("SLICE_WIDTH", "640"))
    OVERLAP_HEIGHT_RATIO: float = float(os.getenv("OVERLAP_HEIGHT_RATIO", "0.2"))
    OVERLAP_WIDTH_RATIO: float = float(os.getenv("OVERLAP_WIDTH_RATIO", "0.2"))
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure required directories exist."""
        Path(cls.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
        Path(cls.TEMP_DIR).mkdir(parents=True, exist_ok=True)
        Path("models").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
    
    @classmethod
    def get_allowed_extensions_set(cls) -> set:
        """Get allowed extensions as a set for fast lookup."""
        return {ext.strip().lower() for ext in cls.ALLOWED_EXTENSIONS}
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production mode."""
        return not cls.DEBUG and os.getenv("ENVIRONMENT", "development") == "production"
    
    @classmethod
    def validate_config(cls) -> None:
        """Validate critical configuration values."""
        if cls.is_production():
            if cls.SECRET_KEY == "dev-secret-change-in-production":
                raise ValueError("SECRET_KEY must be set in production")
            if not cls.SUPABASE_URL:
                raise ValueError("SUPABASE_URL required in production")
        
        if cls.MAX_FILE_SIZE <= 0:
            raise ValueError("MAX_FILE_SIZE must be positive")
        
        if not (0 <= cls.CONFIDENCE_THRESHOLD <= 1):
            raise ValueError("CONFIDENCE_THRESHOLD must be between 0 and 1")

# Global settings instance
settings = Config()

# Ensure directories exist and validate config on import
settings.ensure_directories()
settings.validate_config() 