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
        
        # CRITICAL STEP: Check client availability and reset memory if needed
        # This prevents AI from generating fake clients when insufficient clients are available
        if service._memory_enabled:
            from app.services.memory_reset_service import MemoryResetService
            
            # Get original data to check availability
            original_data = service._data_client.query(query_params)
            
            # Create reset service
            reset_service = MemoryResetService(
                memory_store=service._memory_store,
                mongodb_client=service._data_client
            )
            
            # Check each executive
            reset_actions = []
            for ejecutivo in original_data:
                exec_id = str(ejecutivo.get("id_ejecutivo", ""))
                exec_name = ejecutivo.get("nombre_ejecutivo", "")
                cartera = ejecutivo.get("cartera_detallada", [])
                
                # Apply pre-filtering to see how many clients remain available
                import os
                prefilter_days = int(os.getenv("PREFILTER_DAYS_THRESHOLD", "7"))
                
                # Count available clients (without recent memory_recs)
                from datetime import datetime, timedelta
                if request.current_date:
                    ref_dt = datetime.fromisoformat(request.current_date.split('T')[0])
                else:
                    ref_dt = datetime.utcnow()
                
                cutoff_date = ref_dt - timedelta(days=prefilter_days)
                cutoff_str = cutoff_date.isoformat()
                
                available_clients = []
                for cliente in cartera:
                    memory_recs = cliente.get("memory_recs", [])
                    has_recent_rec = False
                    
                    if memory_recs:
                        for rec in memory_recs:
                            rec_timestamp = rec.get("timestamp", "")
                            if rec_timestamp:
                                rec_date = rec_timestamp.split('T')[0] if 'T' in rec_timestamp else rec_timestamp[:10]
                                cutoff_date_str = cutoff_str.split('T')[0] if 'T' in cutoff_str else cutoff_str[:10]
                                
                                if rec_date > cutoff_date_str:
                                    has_recent_rec = True
                                    break
                    
                    if not has_recent_rec:
                        available_clients.append(cliente)
                
                # Check and reset if needed
                reset_result = reset_service.check_and_reset_if_needed(
                    executive_id=exec_id,
                    available_clients=available_clients,
                    required_recommendations=3,
                    days_threshold=prefilter_days,
                    reference_date=request.current_date
                )
                
                if reset_result['action'] != 'none':
                    logger.warning(f"Executive {exec_name} ({exec_id}): {reset_result['message']}")
                    reset_actions.append({
                        "executive_id": exec_id,
                        "executive_name": exec_name,
                        "action": reset_result['action'],
                        "embeddings_deleted": reset_result['embeddings_deleted']
                    })
            
            if reset_actions:
                logger.info(f"Memory reset executed for {len(reset_actions)} executives")
        
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
        parsed_analysis = json.loads(analysis_text) if analysis_text.strip().startswith(("{", "[")) else None
        
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
            # Create notification service with appropriate testing mode
            notification_service = get_notification_service(is_testing=request.is_testing)
            
            # Send notifications
            notification_result = notification_service.send_analysis_notifications(
                analysis_result={"data": parsed_analysis},
                current_date=request.current_date
            )
            
            response_data["email_notifications"] = notification_result
            logger.info(f"Email notifications sent: {notification_result['total_sent']} successful, {notification_result['total_failed']} failed")
            
            # Store recommendations in database after successful analysis
            if service._memory_enabled and isinstance(parsed_analysis, dict):
                logger.info("Validating and storing recommendations...")
                stored_count = 0
                filtered_count = 0
                invalid_count = 0
                
                # Get original data to validate client ownership
                original_data = service._data_client.query(query_params)
                
                # Build mapping of executive_id -> client_ruts
                exec_clients_map = {}
                for exec_data in original_data:
                    exec_id = str(exec_data.get("id_ejecutivo", ""))
                    cartera = exec_data.get("cartera_detallada", [])
                    client_ruts = set(str(c.get("rut_key")) for c in cartera)
                    exec_clients_map[exec_id] = client_ruts
                
                ejecutivos = parsed_analysis.get("ejecutivos", [])
                for ejecutivo in ejecutivos:
                    executive_id = str(ejecutivo.get("id_ejecutivo", ""))
                    sugerencias = ejecutivo.get("sugerencias_clientes", [])
                    
                    # Validate: should have exactly 3 recommendations
                    if len(sugerencias) != 3:
                        logger.warning(f"Executive {executive_id} has {len(sugerencias)} recommendations (expected 3)")
                    
                    for sugerencia in sugerencias:
                        client_rut = str(sugerencia.get("cliente_rut", ""))
                        
                        if not client_rut or not executive_id:
                            invalid_count += 1
                            logger.warning(f"Invalid recommendation: missing executive_id or client_rut")
                            continue
                        
                        # Validate: client belongs to executive's portfolio
                        if executive_id in exec_clients_map:
                            if client_rut not in exec_clients_map[executive_id]:
                                invalid_count += 1
                                logger.warning(f"Invalid recommendation: Client {client_rut} does not belong to executive {executive_id}")
                                continue
                        
                        # Build recommendation text
                        rec_text = f"{sugerencia.get('accion', '')} - {sugerencia.get('razon', '')}"
                        
                        # Check against historical recommendations
                        historical_recs = service._memory_store.get_historical_recommendations(
                            executive_id=executive_id,
                            client_id=client_rut,
                            limit=10
                        )
                        
                        # Generate embedding for new recommendation
                        new_embedding = service._embedding_client.generate_embedding(rec_text)
                        new_rec = {"recommendation": rec_text, "embedding": new_embedding}
                        
                        # Check similarity with historical recommendations
                        should_filter, matching_rec = service._similarity_service.check_recommendation_similarity(
                            new_recommendation=new_rec,
                            historical_recommendations=historical_recs
                        )
                        
                        if should_filter:
                            filtered_count += 1
                            logger.info(f"Filtered recommendation for executive {executive_id}, client {client_rut} (similar to recent)")
                            continue
                        
                        # Store using memory store (with embeddings)
                        service._memory_store.store_recommendation(
                            executive_id=executive_id,
                            client_id=client_rut,
                            recommendation_text=rec_text,
                            metadata={
                                "prioridad": sugerencia.get("prioridad"),
                                "accion": sugerencia.get("accion"),
                                "origen": sugerencia.get("origen"),
                                "cliente_nombre": sugerencia.get("cliente_nombre"),
                                "status": "repeated_no_change" if matching_rec else "new"
                            }
                        )
                        stored_count += 1
                
                logger.info(f"Recommendations processed: {stored_count} stored, {filtered_count} filtered, {invalid_count} invalid")
                response_data["recommendations_stored"] = stored_count
                response_data["recommendations_filtered"] = filtered_count
                response_data["recommendations_invalid"] = invalid_count
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


@router.get(
    "/health/sendgrid/test",
    status_code=status.HTTP_200_OK,
    summary="Test SendGrid email sending",
    tags=["health"]
)
async def health_check_sendgrid_test() -> dict:
    """
    Test actual email sending with SendGrid.
    
    This endpoint attempts to send a real test email to verify that:
    - SendGrid API is accessible
    - Authentication is working
    - Network/firewall allows SMTP connections
    - SSL certificates are properly configured
    
    Returns:
        - status: "success" or "failed"
        - message: Result message
        - details: Additional information about the test
    """
    try:
        if _settings is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Settings not initialized"
            )
        
        # Check if SendGrid is configured
        if not _settings.sendgrid_api_key or not _settings.sendgrid_from_email:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SendGrid not configured"
            )
        
        # Create email client
        email_client = SendGridEmailClient(
            api_key=_settings.sendgrid_api_key,
            from_email=_settings.sendgrid_from_email,
            is_testing=True,
            test_email_override=_settings.sendgrid_test_email or "test@example.com"
        )
        
        # Attempt to send a test email
        result = email_client.send_email(
            to_email="health-check@example.com",
            subject="SendGrid Health Check Test",
            html_content="<p>This is an automated health check test email.</p>"
        )
        
        if result["success"]:
            return {
                "status": "success",
                "message": "Test email sent successfully",
                "details": {
                    "recipient": result["recipient"],
                    "status_code": result["status_code"]
                }
            }
        else:
            return {
                "status": "failed",
                "message": "Failed to send test email",
                "details": {
                    "error": result["message"]
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SendGrid test error: {str(e)}")
        return {
            "status": "failed",
            "message": "SendGrid test failed",
            "details": {
                "error": str(e)
            }
        }


@router.get(
    "/health/embedding",
    status_code=status.HTTP_200_OK,
    summary="Check Embedding Service connection",
    tags=["health"]
)
async def health_check_embedding(
    service: Annotated[AnalysisService, Depends(get_analysis_service)]
) -> dict:
    """
    Check Embedding Service connection status.
    
    Returns:
        - status: "connected", "disabled", or "not_configured"
        - message: Connection status message
        - model: Model name being used
        - memory_enabled: Whether memory system is enabled
    """
    try:
        if _settings is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Settings not initialized"
            )
        
        # Check if memory system is enabled
        if not _settings.memory_enabled:
            return {
                "status": "disabled",
                "message": "Memory system is disabled by configuration",
                "memory_enabled": False
            }
        
        # Check if embedding client is configured
        if not service._embedding_client:
            return {
                "status": "not_configured",
                "message": "Embedding client not initialized",
                "memory_enabled": _settings.memory_enabled
            }
        
        # Try to generate a test embedding
        try:
            test_text = "Test connection"
            embedding = service._embedding_client.generate_embedding(test_text)
            
            return {
                "status": "connected",
                "message": "Embedding service is healthy",
                "model": _settings.embedding_model_name,
                "memory_enabled": True,
                "embedding_dimension": len(embedding),
                "test_embedding_sample": embedding[:5]  # First 5 values
            }
            
        except ConnectionError as e:
            logger.error(f"Embedding service connection failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Embedding service connection failed: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding service health check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding service health check error: {str(e)}"
        )
