# app/models/user.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class User(BaseModel):
    """Minimal user schema for MVP authentication and access tracking."""
    id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User display name")
    is_active: bool = Field(default=True, description="User account status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User display name")


class UserResponse(BaseModel):
    """Response schema for user operations."""
    success: bool = Field(True, description="Operation success status")
    message: str = Field("User operation successful", description="Response message")
    data: User = Field(..., description="User data")


class UserSession(BaseModel):
    """Minimal session tracking for access logs."""
    user_id: str = Field(..., description="Associated user ID")
    session_id: str = Field(..., description="Unique session identifier")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session start time")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last activity time")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserStats(BaseModel):
    """User activity statistics for tracking."""
    user_id: str = Field(..., description="User identifier")
    total_uploads: int = Field(default=0, description="Total images uploaded")
    total_annotations: int = Field(default=0, description="Total annotations created")
    storage_used_bytes: int = Field(default=0, description="Storage space used in bytes")
    storage_used_formatted: str = Field(default="0 B", description="Human-readable storage usage")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 