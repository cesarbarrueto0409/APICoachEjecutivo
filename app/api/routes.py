"""API routes for the AWS Bedrock API Service."""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Annotated
import logging
import json

from app.api.schemas import AnalysisRequest, AnalysisResponse
from app.services.analysis_service import AnalysisService, ServiceError

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


def set_analysis_service(service: AnalysisService) -> None:
    """Set the global analysis service instance."""
    global _analysis_service
    if service is None:
        raise ValueError("Analysis service cannot be None")
    _analysis_service = service
    logger.info("Analysis service configured")


def get_analysis_service() -> AnalysisService:
    """Dependency injection for AnalysisService."""
    if _analysis_service is None:
        logger.error("Analysis service not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    return _analysis_service


@router.post(
    "/analyze",
    status_code=status.HTTP_200_OK,
    summary="Analyze sales data using predefined queries"
)
async def analyze_data(
    request: AnalysisRequest,
    service: Annotated[AnalysisService, Depends(get_analysis_service)]
):
    """
    POST endpoint for sales analysis.
    
    Uses predefined queries from app.config.queries module.
    Only requires current_date as input.
    """
    try:
        # Import queries configuration
        from app.config.queries import get_queries, get_analysis_prompt
        
        logger.info(f"Processing analysis with date: {request.current_date}")
        
        # Generate queries and prompt based on current_date
        queries = get_queries(request.current_date)
        analysis_prompt = get_analysis_prompt(request.current_date)
        
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
        
        # Try to parse as JSON if it looks like JSON
        try:
            if analysis_text.strip().startswith("{") or analysis_text.strip().startswith("["):
                parsed_analysis = json.loads(analysis_text)
                # Return the parsed JSON directly with metadata
                return {
                    "data": parsed_analysis,
                    "metadata": {
                        "data_count": result["data_count"],
                        "model": analysis_result.get("metadata", {}).get("model"),
                        "tokens": analysis_result.get("metadata", {}).get("tokens"),
                        "cost": analysis_result.get("metadata", {}).get("cost")
                    }
                }
        except json.JSONDecodeError:
            pass
        
        # If not JSON, return as text with metadata
        return {
            "data": {
                "analysis": analysis_text,
                "data_count": result["data_count"]
            },
            "metadata": {
                "model": analysis_result.get("metadata", {}).get("model"),
                "tokens": analysis_result.get("metadata", {}).get("tokens"),
                "cost": analysis_result.get("metadata", {}).get("cost")
            }
        }
        
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
