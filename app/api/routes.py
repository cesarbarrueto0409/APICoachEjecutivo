"""API routes for the AWS Bedrock API Service."""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Annotated, Optional
import logging
import json

from app.api.schemas import AnalysisRequest
from app.services.analysis_service import AnalysisService, ServiceError
from app.services.email_notification_service import EmailNotificationService
from app.clients.email_client import SendGridEmailClient
from app.config.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["analysis"],
    responses={
        400: {"description": "Bad Request"},
        500: {"description": "Internal Server Error"},
        502: {"description": "Bad Gateway"},
        503: {"description": "Service Unavailable"}
    }
)

_analysis_service: AnalysisService = None
_settings: Optional[Settings] = None


def set_analysis_service(service: AnalysisService) -> None:
    """Set the global analysis service instance."""
    global _analysis_service
    if service is None:
        raise ValueError("Analysis service cannot be None")
    _analysis_service = service
    logger.info("Analysis service configured")


def set_settings(settings: Settings) -> None:
    """Set the global settings instance."""
    global _settings
    if settings is None:
        raise ValueError("Settings cannot be None")
    _settings = settings
    logger.info("Settings configured")


def get_analysis_service() -> AnalysisService:
    """Dependency injection for AnalysisService."""
    if _analysis_service is None:
        logger.error("Analysis service not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    return _analysis_service


def get_notification_service(is_testing: bool = False) -> EmailNotificationService:
    """
    Dependency injection for EmailNotificationService.
    
    Args:
        is_testing: Whether to use testing mode for email client
        
    Returns:
        EmailNotificationService instance
    """
    if _settings is None:
        logger.error("Settings not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    # Create email client with appropriate mode
    email_client = SendGridEmailClient(
        api_key=_settings.sendgrid_api_key,
        from_email=_settings.sendgrid_from_email,
        is_testing=is_testing,
        test_email_override=_settings.sendgrid_test_email
    )
    
    return EmailNotificationService(email_client)


@router.post(
    "/analyze",
    status_code=status.HTTP_200_OK,
    summary="Analyze sales data and send email notifications"
)
async def analyze_data(
    request: AnalysisRequest,
    service: Annotated[AnalysisService, Depends(get_analysis_service)]
):
    """
    POST endpoint for sales analysis with email notifications.
    
    Uses predefined queries from app.config.queries module.
    Executes analysis and sends email notifications to ejecutivos.
    """
    try:
        # Import queries configuration
        from app.config.queries import get_queries, get_analysis_prompt
        
        logger.info(f"Processing analysis with date: {request.current_date}, is_testing: {request.is_testing}")
        
        # Generate queries and prompt based on current_date
        queries = get_queries(request.current_date)
        
        # Pass MongoDB client to get_analysis_prompt to fetch from database
        analysis_prompt = get_analysis_prompt(
            request.current_date,
            mongodb_client=service._data_client
        )
        
        if not queries or len(queries) == 0:
            raise ValueError("No queries could be generated")
        
        query_config = queries[0]  # Use the first query
        
        # Build query params from the predefined query
        query_params = {
            "collection": query_config["collection"],
        }
        
        # Add pipeline or filter based on query configuration
        if "pipeline" in query_config:
            query_params["pipeline"] = query_config["pipeline"]
        else:
            if "filter" in query_config:
                query_params["filter"] = query_config["filter"]
            if "projection" in query_config:
                query_params["projection"] = query_config["projection"]
            if "limit" in query_config:
                query_params["limit"] = query_config["limit"]
        
        # Execute analysis with dynamically generated prompt
        result = service.execute_analysis(
            query_params=query_params,
            analysis_prompt=analysis_prompt,
            current_date=request.current_date
        )
        
        logger.info(f"Analysis completed: {result['data_count']} documents")
        
        # Extract the analysis text from the result
        analysis_result = result.get("analysis", {})
        analysis_text = analysis_result.get("analysis", "")
        
        # Parse analysis result
        parsed_analysis = None
        try:
            if analysis_text.strip().startswith("{") or analysis_text.strip().startswith("["):
                parsed_analysis = json.loads(analysis_text)
        except json.JSONDecodeError:
            pass
        
        # Prepare base response
        response_data = {
            "data": parsed_analysis if parsed_analysis else {
                "analysis": analysis_text,
                "data_count": result["data_count"]
            },
            "metadata": {
                "data_count": result["data_count"],
                "model": analysis_result.get("metadata", {}).get("model"),
                "tokens": analysis_result.get("metadata", {}).get("tokens"),
                "cost": analysis_result.get("metadata", {}).get("cost")
            }
        }
        
        # Send email notifications if data exists
        if result["data_count"] > 0 and parsed_analysis:
            try:
                # Create notification service with appropriate testing mode
                notification_service = get_notification_service(is_testing=request.is_testing)
                
                # Send notifications
                notification_result = notification_service.send_analysis_notifications(
                    analysis_result={"data": parsed_analysis},
                    current_date=request.current_date
                )
                
                response_data["email_notifications"] = notification_result
                logger.info(
                    f"Email notifications sent: {notification_result['total_sent']} successful, "
                    f"{notification_result['total_failed']} failed"
                )
                
            except Exception as e:
                logger.error(f"Failed to send email notifications: {str(e)}")
                response_data["email_notifications"] = {
                    "total_sent": 0,
                    "total_failed": 0,
                    "notifications": [],
                    "error": str(e)
                }
        else:
            # No data to send emails for
            response_data["email_notifications"] = {
                "total_sent": 0,
                "total_failed": 0,
                "notifications": []
            }
            if result["data_count"] == 0:
                logger.info("No email notifications sent: data_count is 0")
        
        return response_data
        
    except ValueError as e:
        error_msg = f"Invalid request: {str(e)}"
        logger.warning(error_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
        
    except ServiceError as e:
        error_msg = f"{e.message}"
        if e.details:
            error_msg += f": {e.details}"
        
        logger.error(f"Service error at '{e.step}': {error_msg}")
        
        if e.step == "data_retrieval":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE if "connect" in e.message.lower() else status.HTTP_400_BAD_REQUEST
        elif e.step == "ai_analysis":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE if "connect" in e.message.lower() else status.HTTP_502_BAD_GATEWAY
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        raise HTTPException(status_code=status_code, detail=error_msg)
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(error_msg)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)


@router.get("/health", status_code=status.HTTP_200_OK, summary="Health check", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "AWS Bedrock API Service"}


@router.get(
    "/health/mongodb",
    status_code=status.HTTP_200_OK,
    summary="Check MongoDB connection",
    tags=["health"]
)
async def health_check_mongodb(
    service: Annotated[AnalysisService, Depends(get_analysis_service)]
) -> dict:
    """
    Check MongoDB connection status.
    
    Returns:
        - status: "connected" or "disconnected"
        - message: Connection status message
        - database: Database name
    """
    try:
        # Try to execute a simple query to verify connection
        test_query = {
            "collection": "clientes_por_ejecutivo",
            "filter": {},
            "limit": 1
        }
        
        # Access the private data client through the service
        # This is a simple ping test
        result = service._data_client.query(test_query)
        
        return {
            "status": "connected",
            "message": "MongoDB connection is healthy",
            "database": _settings.mongodb_database if _settings else "unknown"
        }
        
    except ConnectionError as e:
        logger.error(f"MongoDB connection failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MongoDB connection failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"MongoDB health check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MongoDB health check error: {str(e)}"
        )


@router.get(
    "/health/bedrock",
    status_code=status.HTTP_200_OK,
    summary="Check AWS Bedrock connection",
    tags=["health"]
)
async def health_check_bedrock(
    service: Annotated[AnalysisService, Depends(get_analysis_service)]
) -> dict:
    """
    Check AWS Bedrock connection status.
    
    Returns:
        - status: "connected" or "disconnected"
        - message: Connection status message
        - model: Model ID being used
        - region: AWS region
    """
    try:
        # Try to execute a simple analysis to verify connection
        test_data = [{"test": "connection check"}]
        test_prompt = "Respond with: OK"
        
        result = service._ai_client.analyze(test_data, prompt=test_prompt)
        
        return {
            "status": "connected",
            "message": "AWS Bedrock connection is healthy",
            "model": _settings.aws_bedrock_model_id if _settings else "unknown",
            "region": _settings.aws_region if _settings else "unknown",
            "test_response": result.get("analysis", "")[:100]  # First 100 chars
        }
        
    except ConnectionError as e:
        logger.error(f"AWS Bedrock connection failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AWS Bedrock connection failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"AWS Bedrock health check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AWS Bedrock health check error: {str(e)}"
        )


@router.get(
    "/health/sendgrid",
    status_code=status.HTTP_200_OK,
    summary="Check SendGrid connection",
    tags=["health"]
)
async def health_check_sendgrid() -> dict:
    """
    Check SendGrid configuration status.
    
    Note: This endpoint only validates configuration, not actual email sending.
    To test email sending, use the /api/analyze endpoint with is_testing=true.
    
    Returns:
        - status: "configured" or "not_configured"
        - message: Configuration status message
        - from_email: Configured sender email
        - test_email: Configured test email
    """
    try:
        if _settings is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Settings not initialized"
            )
        
        # Check if SendGrid is properly configured
        if not _settings.sendgrid_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SendGrid API key not configured"
            )
        
        if not _settings.sendgrid_from_email:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SendGrid from_email not configured"
            )
        
        # Try to create a client to verify configuration
        try:
            email_client = SendGridEmailClient(
                api_key=_settings.sendgrid_api_key,
                from_email=_settings.sendgrid_from_email,
                is_testing=True,
                test_email_override=_settings.sendgrid_test_email or "test@example.com"
            )
            
            return {
                "status": "configured",
                "message": "SendGrid is properly configured",
                "from_email": _settings.sendgrid_from_email,
                "test_email": _settings.sendgrid_test_email or "not configured",
                "note": "Use /api/analyze with is_testing=true to test actual email sending"
            }
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"SendGrid configuration error: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SendGrid health check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SendGrid health check error: {str(e)}"
        )
