"""
Request and response schemas for the API endpoints.

This module defines Pydantic models for validating and serializing API requests
and responses. These schemas ensure type safety, provide automatic validation of
incoming data, and generate OpenAPI documentation automatically.

Pydantic models provide:
    - Automatic data validation
    - Type coercion and conversion
    - JSON schema generation for OpenAPI docs
    - Clear error messages for invalid data
    - IDE autocomplete support

Example:
    Using schemas for validation:
    >>> from app.api.schemas import AnalysisRequest
    >>> request = AnalysisRequest(current_date="2024-02-18", is_testing=True)
    >>> print(request.current_date)  # "2024-02-18"
    >>> print(request.is_testing)  # True
    
    Invalid data raises validation error:
    >>> try:
    ...     request = AnalysisRequest(current_date="invalid-date")
    ... except ValidationError as e:
    ...     print(e)  # Shows validation errors
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class AnalysisRequest(BaseModel):
    """
    Request model for the analysis endpoint.
    
    This schema defines the structure and validation rules for POST /api/analyze requests.
    It ensures that the current_date is provided and is_testing is a boolean value.
    
    Attributes:
        current_date (str): Date for analysis context in YYYY-MM-DD format.
            This date determines which month's data to retrieve and is used for
            filtering sales, claims, and pickup data. Must be a valid date string.
            
        is_testing (bool): Whether to use testing mode for email notifications.
            If True, all emails are redirected to the test email address configured
            in SENDGRID_TEST_EMAIL. Default is False (production mode).
    
    Example:
        Create a request for production:
        >>> request = AnalysisRequest(current_date="2024-02-18", is_testing=False)
        >>> print(request.dict())
        {'current_date': '2024-02-18', 'is_testing': False}
        
        Create a request for testing:
        >>> request = AnalysisRequest(current_date="2024-02-18", is_testing=True)
        >>> # All emails will be sent to test address
        
        Use in FastAPI endpoint:
        >>> @router.post("/api/analyze")
        >>> async def analyze(request: AnalysisRequest):
        ...     print(f"Analyzing data for {request.current_date}")
        ...     if request.is_testing:
        ...         print("Running in test mode")
    """
    
    current_date: str = Field(
        ...,
        description="Current date for analysis context (YYYY-MM-DD)",
        example="2026-02-11"
    )
    is_testing: bool = Field(
        default=False,
        description="If True, send all emails to test address",
        example=False
    )
    
    class Config:
        """Pydantic configuration for the model."""
        json_schema_extra = {
            "example": {
                "current_date": "2026-02-11",
                "is_testing": False
            }
        }


class EmailNotification(BaseModel):
    """
    Model for individual email notification result.
    
    This schema represents the result of sending a single email notification
    to an executive. It includes information about the recipient, email content,
    delivery status, and any errors that occurred.
    
    Attributes:
        ejecutivo (str): Name of the executive who received the email
        recipient (str, optional): Actual email address where the email was sent
        original_recipient (str, optional): Original intended recipient (when in testing mode)
        subject (str, optional): Email subject line
        body (str, optional): Email body content (HTML)
        status (str): Delivery status - either 'success' or 'failed'
        status_code (int, optional): HTTP status code from SendGrid API
        error (str, optional): Error message if delivery failed
    
    Example:
        Successful email notification:
        >>> notification = EmailNotification(
        ...     ejecutivo="John Doe",
        ...     recipient="john@company.com",
        ...     subject="Daily Report",
        ...     status="success",
        ...     status_code=202
        ... )
        
        Failed email notification:
        >>> notification = EmailNotification(
        ...     ejecutivo="Jane Smith",
        ...     recipient="jane@company.com",
        ...     status="failed",
        ...     error="Invalid API key"
        ... )
        
        Testing mode notification:
        >>> notification = EmailNotification(
        ...     ejecutivo="John Doe",
        ...     recipient="test@company.com",
        ...     original_recipient="john@company.com",
        ...     subject="[TEST] Daily Report",
        ...     status="success",
        ...     status_code=202
        ... )
    """
    
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
