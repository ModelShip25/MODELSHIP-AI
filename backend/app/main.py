# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import time
from app.core.config import settings
from app.routes import upload, clean, label, preview, export

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="ModelShip API",
    description="AI-powered auto-labeling platform for images",
    version="1.0.0"
)

# Add rate limiter error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # List of allowed origins from config
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],  # Required headers
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log request and response details."""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {request.method} {request.url} - Status: {response.status_code} - Time: {process_time:.2f}s"
    )
    
    return response

# Include routers
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(clean.router, prefix="/api/v1/clean", tags=["cleaning"])
app.include_router(label.router, prefix="/api/v1/label", tags=["labeling"])
app.include_router(preview.router, prefix="/api/v1/preview", tags=["preview"])
app.include_router(export.router, prefix="/api/v1/export", tags=["export"])

@app.get("/")
@limiter.limit("10/minute")
async def root():
    """Root endpoint."""
    return {"message": "ModelShip API is running", "version": "1.0.0"}

@app.get("/health")
@limiter.limit("60/minute")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
