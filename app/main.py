"""
Application entry point for the AWS Bedrock API Service.

This module serves as the main entry point for the FastAPI application. It handles:
    - Application initialization and configuration
    - Dependency injection setup
    - Client connections (MongoDB, AWS Bedrock, Embedding Service)
    - Service layer initialization (Analysis, Memory, Similarity, Email)
    - Application lifecycle management (startup/shutdown)
    - CORS middleware configuration

The application follows a factory pattern where create_app() builds and configures
the FastAPI application with all necessary dependencies.

Architecture:
    1. Load configuration from environment variables
    2. Validate configuration
    3. Initialize client layer (MongoDB, AWS Bedrock, Embedding, Email)
    4. Initialize service layer (Analysis, Memory, Similarity, Email Notification)
    5. Configure dependency injection
    6. Register API routes
    7. Start application

Example:
    Run the application:
    >>> python app/main.py
    # Server starts on configured host:port (default: 0.0.0.0:8000)
    
    Or with uvicorn:
    >>> uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    
    Access API documentation:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc
"""

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
from app.services.batch_processor import BatchConfig
from app.api.routes import router, set_analysis_service, set_settings

# Configure logging with timestamp, logger name, level, and message
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global client instances (initialized in setup_dependencies)
_mongodb_client: MongoDBClient = None
_aws_bedrock_client: AWSBedrockClient = None
_embedding_client: EmbeddingClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    This async context manager handles the application lifecycle:
        - Startup: Connects to all external services (MongoDB, AWS Bedrock, Embedding)
        - Shutdown: Disconnects and cleans up resources
    
    The lifespan pattern ensures that connections are properly established before
    the application starts accepting requests and cleanly closed when shutting down.
    
    Args:
        app: FastAPI application instance
    
    Yields:
        Control to the application during its runtime
    
    Raises:
        Exception: If any service fails to initialize during startup
    
    Example:
        This function is automatically called by FastAPI:
        >>> app = FastAPI(lifespan=lifespan)
        # On startup: Connects to all services
        # During runtime: Application handles requests
        # On shutdown: Disconnects from all services
    """
    logger.info("Starting AWS Bedrock API Service...")
    
    # Connect to MongoDB
    if _mongodb_client:
        _mongodb_client.connect()
        logger.info("MongoDB connected")
    
    # Connect to AWS Bedrock
    if _aws_bedrock_client:
        _aws_bedrock_client.connect()
        logger.info("AWS Bedrock connected")
    
    # Connect to Embedding Service (if memory system enabled)
    if _embedding_client:
        _embedding_client.connect()
        logger.info("Embedding service connected")
    
    logger.info("Startup complete")
    
    # Yield control to the application
    yield
    
    # Shutdown phase
    logger.info("Shutting down...")
    
    # Disconnect from MongoDB
    if _mongodb_client:
        _mongodb_client.disconnect()
        logger.info("MongoDB disconnected")
    
    logger.info("Shutdown complete")


def setup_dependencies(app: FastAPI, settings: Settings) -> None:
    """
    Configure dependency injection for the application.
    
    This function initializes all client and service layer components and configures
    them for dependency injection throughout the application. It follows a layered
    architecture:
    
    Layer 1 - Clients (External Services):
        - MongoDBClient: Database operations
        - AWSBedrockClient: AI analysis
        - EmbeddingClient: Text embeddings (optional, if memory enabled)
    
    Layer 2 - Services (Business Logic):
        - SimilarityService: Semantic similarity computation
        - RecommendationMemoryStore: Memory management with embeddings
        - AnalysisService: Main orchestration service
    
    Layer 3 - API Routes:
        - Configured with analysis_service and settings via dependency injection
    
    The function handles optional memory system initialization gracefully, continuing
    without memory features if initialization fails.
    
    Args:
        app: FastAPI application instance
        settings: Validated Settings object with configuration
    
    Example:
        This function is called during application creation:
        >>> app = FastAPI()
        >>> settings = Settings()
        >>> settings.validate()
        >>> setup_dependencies(app, settings)
        # All dependencies are now configured and ready for injection
    """
    global _mongodb_client, _aws_bedrock_client, _embedding_client
    
    logger.info("Setting up dependencies...")
    
    # Initialize client layer - MongoDB (required)
    _mongodb_client = MongoDBClient(settings.mongodb_uri, settings.mongodb_database)
    
    # Initialize client layer - AWS Bedrock (required)
    _aws_bedrock_client = AWSBedrockClient(
        settings.aws_region,
        settings.aws_bedrock_model_id
    )
    
    # Initialize memory system components (optional)
    embedding_client = None
    memory_store = None
    similarity_service = None
    
    if settings.memory_enabled:
        logger.info("Initializing memory system components...")
        
        # Initialize embedding client for generating text embeddings
        _embedding_client = EmbeddingClient(
            api_key=settings.embedding_api_key,
            endpoint=settings.embedding_endpoint,
            model_name=settings.embedding_model_name
        )
        embedding_client = _embedding_client
        
        # Initialize similarity service for semantic comparison
        similarity_service = SimilarityService(
            similarity_threshold=settings.similarity_threshold,
            cooldown_days=settings.cooldown_days
        )
        
        # Initialize recommendation memory store for persistence
        memory_store = RecommendationMemoryStore(
            data_client=_mongodb_client,
            embedding_client=embedding_client
        )
        
        logger.info("Memory system components initialized")
    else:
        logger.info("Memory system disabled by configuration")
    
    # Initialize analysis service with all dependencies
    # Configure batch processing for scalability
    batch_config = BatchConfig(
        batch_size=int(os.getenv("BATCH_SIZE", "5")),  # Executives per batch
        max_parallel_batches=int(os.getenv("MAX_PARALLEL_BATCHES", "20")),  # Respect rate limits
        enable_parallel=os.getenv("ENABLE_PARALLEL_BATCHES", "true").lower() == "true"
    )
    
    logger.info(
        f"Batch processing configured: size={batch_config.batch_size}, "
        f"max_parallel={batch_config.max_parallel_batches}, "
        f"parallel_enabled={batch_config.enable_parallel}"
    )
    
    analysis_service = AnalysisService(
        data_client=_mongodb_client,
        ai_client=_aws_bedrock_client,
        embedding_client=embedding_client,
        memory_store=memory_store,
        similarity_service=similarity_service,
        memory_enabled=settings.memory_enabled,
        batch_config=batch_config
    )
    
    # Configure dependency injection for API routes
    set_analysis_service(analysis_service)
    set_settings(settings)
    
    logger.info("Dependencies configured")


def create_app() -> FastAPI:
    """
    Application factory function.
    
    This function creates and configures a FastAPI application instance with all
    necessary middleware, routes, and dependencies. It follows the factory pattern
    to allow for flexible application creation and testing.
    
    The function performs the following steps:
        1. Load configuration from environment variables
        2. Validate configuration (raises ValueError if invalid)
        3. Create FastAPI application with metadata
        4. Add CORS middleware for cross-origin requests
        5. Setup dependency injection
        6. Register API routes
    
    Returns:
        Configured FastAPI application instance ready to serve requests
    
    Raises:
        ValueError: If configuration validation fails
    
    Example:
        Create and run application:
        >>> app = create_app()
        >>> import uvicorn
        >>> uvicorn.run(app, host="0.0.0.0", port=8000)
        
        For testing:
        >>> from fastapi.testclient import TestClient
        >>> app = create_app()
        >>> client = TestClient(app)
        >>> response = client.get("/api/health")
        >>> assert response.status_code == 200
    """
    logger.info("Loading configuration...")
    settings = Settings()
    
    settings.validate()
    logger.info("Configuration validated")
    
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


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = Settings()
    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=True, log_level="info")
