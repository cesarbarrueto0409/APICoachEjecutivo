"""
Client layer for external service integrations.
"""

from app.clients.interfaces import IDataClient, IAIClient
from app.clients.mongodb_client import MongoDBClient
from app.clients.aws_bedrock_client import AWSBedrockClient

__all__ = [
    'IDataClient',
    'IAIClient',
    'MongoDBClient',
    'AWSBedrockClient',
]
