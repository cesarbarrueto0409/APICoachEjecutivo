"""
Configuration management for the AWS Bedrock API Service.

This module handles loading and validation of all application configuration from
environment variables. It uses python-dotenv to load variables from .env files
and provides a centralized Settings class for accessing configuration throughout
the application.

Configuration Groups:
    - MongoDB: Database connection settings
    - AWS Bedrock: AI service configuration
    - SendGrid: Email service settings
    - Embedding Service: Text embedding API configuration
    - Memory System: Similarity and cooldown settings
    - API: Server host and port settings

Example:
    Load and validate configuration:
    >>> from app.config.settings import Settings
    >>> settings = Settings()
    >>> settings.validate()  # Raises ValueError if invalid
    >>> print(f"MongoDB: {settings.mongodb_database}")
    >>> print(f"Model: {settings.aws_bedrock_model_id}")
    >>> print(f"Memory enabled: {settings.memory_enabled}")
"""

import os
from dotenv import load_dotenv


class Settings:
    """
    Manages application configuration from environment variables.
    
    This class loads configuration from environment variables (typically from a .env file)
    and provides typed access to all settings. It includes validation to ensure all
    required configuration is present before the application starts.
    
    The class automatically loads environment variables using python-dotenv when
    instantiated, making configuration available immediately.
    
    Attributes:
        mongodb_uri (str): MongoDB connection string (e.g., "mongodb+srv://user:pass@cluster.mongodb.net/")
        mongodb_database (str): Name of the MongoDB database to use
        aws_region (str): AWS region for Bedrock service (default: "us-east-1")
        aws_bedrock_model_id (str): Bedrock model ID or inference profile ARN
        sendgrid_api_key (str): SendGrid API key for email sending
        sendgrid_endpoint (str): SendGrid API endpoint URL
        sendgrid_from_email (str): Default sender email address
        sendgrid_test_email (str): Email address for testing mode
        embedding_api_key (str): API key for embedding service (OpenAI)
        embedding_endpoint (str): Embedding service API endpoint
        embedding_model_name (str): Name of embedding model (default: "text-embedding-3-large")
        similarity_threshold (float): Threshold for similarity matching (default: 0.85)
        cooldown_days (int): Days before allowing similar recommendations (default: 14)
        memory_enabled (bool): Whether memory system is enabled (default: True)
        api_host (str): API server host (default: "0.0.0.0")
        api_port (int): API server port (default: 8000)
    
    Example:
        Basic usage:
        >>> settings = Settings()
        >>> settings.validate()
        >>> print(f"Connecting to: {settings.mongodb_database}")
        >>> print(f"Memory enabled: {settings.memory_enabled}")
        
        Access configuration:
        >>> if settings.memory_enabled:
        ...     print(f"Similarity threshold: {settings.similarity_threshold}")
        ...     print(f"Cooldown period: {settings.cooldown_days} days")
        
        Check specific settings:
        >>> if settings.sendgrid_api_key:
        ...     print("Email notifications enabled")
        >>> if settings.embedding_api_key:
        ...     print("Embedding service configured")
    """
    
    def __init__(self):
        """
        Initialize settings by loading environment variables.
        
        This constructor automatically loads environment variables from a .env file
        (if present) and initializes all configuration attributes with values from
        the environment or sensible defaults.
        
        Environment variables are loaded using python-dotenv, which searches for
        .env files in the current directory and parent directories.
        
        Example:
            >>> settings = Settings()  # Automatically loads .env file
            >>> print(settings.mongodb_uri)  # Access loaded configuration
        """
        load_dotenv()
        
        self.mongodb_uri: str = os.getenv('MONGODB_URI', '')
        self.mongodb_database: str = os.getenv('MONGODB_DATABASE', '')
        self.aws_region: str = os.getenv('AWS_REGION', 'us-east-1')
        self.aws_bedrock_model_id: str = os.getenv(
            'AWS_BEDROCK_MODEL_ID',
            'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        )
        # AWS credentials are handled by boto3 from environment or ~/.aws/credentials
        
        # SendGrid configuration
        self.sendgrid_api_key: str = os.getenv('SENDGRID_API_KEY', '')
        self.sendgrid_endpoint: str = os.getenv(
            'SENDGRID_ENDPOINT',
            'https://api.sendgrid.com/v3/mail/send'
        )
        self.sendgrid_from_email: str = os.getenv('SENDGRID_FROM_EMAIL', '')
        self.sendgrid_test_email: str = os.getenv('SENDGRID_TEST_EMAIL', '')
        
        # Embedding service configuration
        self.embedding_api_key: str = os.getenv('EMBEDDING_API_KEY', '')
        self.embedding_endpoint: str = os.getenv('EMBEDDING_ENDPOINT', '')
        self.embedding_model_name: str = os.getenv(
            'EMBEDDING_MODEL_NAME',
            'text-embedding-3-large'
        )
        
        # Memory system configuration
        self.similarity_threshold: float = float(os.getenv('SIMILARITY_THRESHOLD', '0.85'))
        self.cooldown_days: int = int(os.getenv('COOLDOWN_DAYS', '14'))
        self.memory_enabled: bool = os.getenv('MEMORY_ENABLED', 'true').lower() == 'true'
        
        # API server configuration
        self.api_host: str = os.getenv('API_HOST', '0.0.0.0')
        self.api_port: int = int(os.getenv('API_PORT', '8000'))
    
    def validate(self) -> None:
        """
        Validate that all required configuration values are present and valid.
        
        This method checks that all required environment variables are set and that
        numeric values are within acceptable ranges. It should be called after
        instantiation and before starting the application to ensure proper configuration.
        
        Validation checks performed:
            1. Required fields are non-empty:
               - MONGODB_URI, MONGODB_DATABASE
               - AWS_REGION, AWS_BEDROCK_MODEL_ID
               - SENDGRID_API_KEY
            
            2. Memory system fields (if memory_enabled=True):
               - EMBEDDING_API_KEY, EMBEDDING_ENDPOINT
            
            3. Numeric ranges:
               - similarity_threshold must be between 0 and 1
               - cooldown_days must be positive
        
        Raises:
            ValueError: If any required configuration is missing or invalid.
                The error message lists all missing/invalid configuration keys.
        
        Example:
            Successful validation:
            >>> settings = Settings()
            >>> settings.validate()  # No error means configuration is valid
            >>> print("Configuration is valid!")
            
            Handle validation errors:
            >>> settings = Settings()
            >>> try:
            ...     settings.validate()
            ... except ValueError as e:
            ...     print(f"Configuration error: {e}")
            ...     # Fix configuration and retry
            
            Check specific validation:
            >>> settings = Settings()
            >>> if not 0 <= settings.similarity_threshold <= 1:
            ...     print("Invalid similarity threshold!")
        """
        missing_configs = []
        
        if not self.mongodb_uri:
            missing_configs.append('MONGODB_URI')
        if not self.mongodb_database:
            missing_configs.append('MONGODB_DATABASE')
        if not self.aws_region:
            missing_configs.append('AWS_REGION')
        if not self.aws_bedrock_model_id:
            missing_configs.append('AWS_BEDROCK_MODEL_ID')
        if not self.sendgrid_api_key:
            missing_configs.append('SENDGRID_API_KEY')
        
        # Memory system validation (only if enabled)
        if self.memory_enabled:
            if not self.embedding_api_key:
                missing_configs.append('EMBEDDING_API_KEY')
            if not self.embedding_endpoint:
                missing_configs.append('EMBEDDING_ENDPOINT')
        
        if missing_configs:
            missing_list = ', '.join(missing_configs)
            raise ValueError(f"Missing required configuration: {missing_list}")
        
        # Validate numeric ranges
        if not 0 <= self.similarity_threshold <= 1:
            raise ValueError("SIMILARITY_THRESHOLD must be between 0 and 1")
        
        if self.cooldown_days <= 0:
            raise ValueError("COOLDOWN_DAYS must be positive")
    
    def __repr__(self) -> str:
        """
        Return string representation of Settings instance.
        
        This method provides a readable string representation showing key
        configuration values. Sensitive information like API keys are not included.
        
        Returns:
            String representation of the Settings object
        
        Example:
            >>> settings = Settings()
            >>> print(settings)
            Settings(mongodb_uri='mongodb://localhost', mongodb_database='sales_db', ...)
        """
        return (
            f"Settings(mongodb_uri='{self.mongodb_uri}', "
            f"mongodb_database='{self.mongodb_database}', "
            f"aws_region='{self.aws_region}', "
            f"aws_bedrock_model_id='{self.aws_bedrock_model_id}', "
            f"api_host='{self.api_host}', api_port={self.api_port})"
        )
