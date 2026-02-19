"""Application entry point for the AWS Bedrock API Service."""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import Settings
from app.clients.mongodb_client import MongoDBClient
from app.clients.aws_bedrock_client import AWSBedrockClient
from app.clients.embedding_client import EmbeddingClient
from app.services.analysis_service import AnalysisService
from app.services.recommendation_memory_store import RecommendationMemoryStore
from app.services.similarity_service import SimilarityService
from app.api.routes import router, set_analysis_service, set_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_mongodb_client: MongoDBClient = None
_aws_bedrock_client: AWSBedrockClient = None
_embedding_client: EmbeddingClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting AWS Bedrock API Service...")
    
    try:
        if _mongodb_client:
            _mongodb_client.connect()
            logger.info("MongoDB connected")
        
        if _aws_bedrock_client:
            _aws_bedrock_client.connect()
            logger.info("AWS Bedrock connected")
        
        if _embedding_client:
            _embedding_client.connect()
            logger.info("Embedding service connected")
        
        logger.info("Startup complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize: {str(e)}")
        raise
    
    yield
    
    logger.info("Shutting down...")
    
    try:
        if _mongodb_client:
            _mongodb_client.disconnect()
            logger.info("MongoDB disconnected")
        
        logger.info("Shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


def setup_dependencies(app: FastAPI, settings: Settings) -> None:
    """Configure dependency injection."""
    global _mongodb_client, _aws_bedrock_client, _embedding_client
    
    logger.info("Setting up dependencies...")
    
    _mongodb_client = MongoDBClient(settings.mongodb_uri, settings.mongodb_database)
    _aws_bedrock_client = AWSBedrockClient(
        settings.aws_region,
        settings.aws_bedrock_model_id
    )
    
    # Initialize memory system components if enabled
    embedding_client = None
    memory_store = None
    similarity_service = None
    
    if settings.memory_enabled:
        try:
            logger.info("Initializing memory system components...")
            
            # Initialize embedding client
            _embedding_client = EmbeddingClient(
                api_key=settings.embedding_api_key,
                endpoint=settings.embedding_endpoint,
                model_name=settings.embedding_model_name
            )
            embedding_client = _embedding_client
            
            # Initialize similarity service
            similarity_service = SimilarityService(
                similarity_threshold=settings.similarity_threshold,
                cooldown_days=settings.cooldown_days
            )
            
            # Initialize recommendation memory store
            memory_store = RecommendationMemoryStore(
                data_client=_mongodb_client,
                embedding_client=embedding_client
            )
            
            logger.info("Memory system components initialized")
            
        except Exception as e:
            logger.warning(f"Failed to initialize memory system: {e}. Continuing without memory.")
            embedding_client = None
            memory_store = None
            similarity_service = None
    else:
        logger.info("Memory system disabled by configuration")
    
    # Initialize analysis service with memory components
    analysis_service = AnalysisService(
        data_client=_mongodb_client,
        ai_client=_aws_bedrock_client,
        embedding_client=embedding_client,
        memory_store=memory_store,
        similarity_service=similarity_service,
        memory_enabled=settings.memory_enabled
    )
    
    set_analysis_service(analysis_service)
    set_settings(settings)
    
    logger.info("Dependencies configured")


def create_app() -> FastAPI:
    """Application factory."""
    logger.info("Loading configuration...")
    settings = Settings()
    
    try:
        settings.validate()
        logger.info("Configuration validated")
    except ValueError as e:
        logger.error(f"Configuration failed: {str(e)}")
        raise
    
    app = FastAPI(
        title="AWS Bedrock API Service",
        description="REST API integrating MongoDB with AWS Bedrock for data analysis",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    setup_dependencies(app, settings)
    app.include_router(router)
    
    logger.info("Application created")
    return app


try:
    app = create_app()
except ValueError as e:
    logger.warning(f"Could not create app: {str(e)}")
    app = FastAPI(title="AWS Bedrock API Service (Unconfigured)")


if __name__ == "__main__":
    import uvicorn
    settings = Settings()
    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True, log_level="info")
