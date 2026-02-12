"""
Request and response schemas for the API endpoints.

This module defines Pydantic models for validating and serializing
API requests and responses. These schemas ensure type safety and
provide automatic validation of incoming data.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class AnalysisRequest(BaseModel):
    """Request model for the analysis endpoint."""
    
    current_date: str = Field(..., description="Current date for analysis context (YYYY-MM-DD)", example="2026-02-11")
    is_testing: bool = Field(
        default=False,
        description="If True, send all emails to test address",
        example=False
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_date": "2026-02-11",
                "is_testing": False
            }
        }


class EmailNotification(BaseModel):
    """Model for individual email notification result."""
    
    ejecutivo: str = Field(..., description="Name of ejecutivo")
    recipient: Optional[str] = Field(None, description="Email recipient")
    original_recipient: Optional[str] = Field(
        None,
        description="Original recipient (when in testing mode)"
    )
    subject: Optional[str] = Field(None, description="Email subject")
    body: Optional[str] = Field(None, description="Email body content")
    status: str = Field(..., description="'success' or 'failed'")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    error: Optional[str] = Field(None, description="Error message if failed")
