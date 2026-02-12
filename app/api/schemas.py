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
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_date": "2026-02-11"
            }
        }


class AnalysisResponse(BaseModel):
    """Response model for the analysis endpoint."""
    
    status: str = Field(..., description="'success' or 'error'", example="success")
    data_count: int = Field(..., ge=0, description="Number of documents analyzed", example=42)
    analysis: Dict[str, Any] = Field(..., description="AI analysis results", example={"summary": "Analysis results..."})
    error: Optional[str] = Field(default=None, description="Error message if failed", example=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data_count": 42,
                "analysis": {"summary": "Sales analysis shows positive trends"},
                "error": None
            }
        }
