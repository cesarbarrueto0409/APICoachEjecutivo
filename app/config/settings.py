"""Configuration management for the AWS Bedrock API Service."""

import os
from typing import Optional
from dotenv import load_dotenv


class Settings:
    """Manages application configuration from environment variables."""
    
    def __init__(self):
        load_dotenv()
        
        self.mongodb_uri: str = os.getenv('MONGODB_URI', '')
        self.mongodb_database: str = os.getenv('MONGODB_DATABASE', '')
        self.aws_region: str = os.getenv('AWS_REGION', 'us-east-1')
        self.aws_bedrock_model_id: str = os.getenv(
            'AWS_BEDROCK_MODEL_ID',
            'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        )
        # AWS credentials are handled by boto3 from environment or ~/.aws/credentials
        self.api_host: str = os.getenv('API_HOST', '0.0.0.0')
        self.api_port: int = int(os.getenv('API_PORT', '8000'))
    
    def validate(self) -> None:
        """Validate that all required configuration values are present."""
        missing_configs = []
        
        if not self.mongodb_uri:
            missing_configs.append('MONGODB_URI')
        if not self.mongodb_database:
            missing_configs.append('MONGODB_DATABASE')
        if not self.aws_region:
            missing_configs.append('AWS_REGION')
        if not self.aws_bedrock_model_id:
            missing_configs.append('AWS_BEDROCK_MODEL_ID')
        
        if missing_configs:
            missing_list = ', '.join(missing_configs)
            raise ValueError(f"Missing required configuration: {missing_list}")
    
    def __repr__(self) -> str:
        return (
            f"Settings(mongodb_uri='{self.mongodb_uri}', "
            f"mongodb_database='{self.mongodb_database}', "
            f"aws_region='{self.aws_region}', "
            f"aws_bedrock_model_id='{self.aws_bedrock_model_id}', "
            f"api_host='{self.api_host}', api_port={self.api_port})"
        )
