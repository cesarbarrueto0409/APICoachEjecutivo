"""Application entry point for the AWS Bedrock API Service."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import Settings
from app.clients.mongodb_client import MongoDBClient
from app.clients.aws_bedrock_client import AWSBedrockClient
from app.services.analysis_service import AnalysisService
from app.api.routes import router, set_analysis_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

_mongodb_client: MongoDBClient = None
_aws_bedrock_client: AWSBedrockClient = None


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
    global _mongodb_client, _aws_bedrock_client
    
    logger.info("Setting up dependencies...")
    
    _mongodb_client = MongoDBClient(settings.mongodb_uri, settings.mongodb_database)
    _aws_bedrock_client = AWSBedrockClient(
        settings.aws_region,
        settings.aws_bedrock_model_id
    )
    
    analysis_service = AnalysisService(_mongodb_client, _aws_bedrock_client)
    set_analysis_service(analysis_service)
    
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
